# encoding: UTF-8

import logging
import multiprocessing
import Queue
import time
import threading

from photofilmstrip.lib.common.Singleton import Singleton
from .IVisualJobManager import IVisualJobManager
from .LogVisualJobManager import LogVisualJobManager
from .Worker import Worker
from .JobAbortedException import JobAbortedException


class _JobCtxGroup(object):
    
    def __init__(self, ctxGroup, workers):
        self.__ctxGroup = ctxGroup
        self.__idleLock = threading.Lock()
        self.__idleQueue = Queue.Queue()
        self.__activeLock = threading.Lock()
        self.__active = None
        getJobLock = threading.Lock()
        self.__getJobCond = threading.Condition(getJobLock)
       
        getJobLock = threading.Lock()
        self.__getJobCond = threading.Condition(getJobLock)
        
        self.__workers = workers
    
    def Put(self, jobContext):
        self.__idleQueue.put(jobContext)
        self.Notify()
        
    def Notify(self):
        with self.__getJobCond:
            self.__getJobCond.notifyAll()
            
    def Get(self):
        return self.__idleQueue.get(False, None)
            
    def __enter__(self):
        return self
    def __exit__(self, typ, value, traceback):
        pass
    
    def Active(self):
        return self.__active
    
    def SetActive(self, jobContext):
        self.__active = jobContext
        
    def ActiveLock(self):
        return self.__activeLock
        
    def Wait(self, timeout=None):
        with self.__getJobCond:
            self.__getJobCond.wait(timeout)
            
    def Workers(self):
        return self.__workers


class JobManager(Singleton):
    
    DEFAULT_CTXGROUP_ID = "general"
    
    def __init__(self):
        self.__defaultVisual = LogVisualJobManager()
        self.__visuals = [self.__defaultVisual]
        
        self.__destroying = False
        self.__jobCtxGroups = {}
        
        self.__logger = logging.getLogger("JobManager")
        
    def AddVisual(self, visual):
        assert isinstance(visual, IVisualJobManager)
        if self.__defaultVisual in self.__visuals:
            self.__visuals.remove(self.__defaultVisual)

        self.__visuals.append(visual)
    
    def RemoveVisual(self, visual):
        if visual in self.__visuals:
            self.__visuals.remove(visual)
        
        if len(self.__visuals) == 0:
            self.__visuals.append(self.__defaultVisual)
        
    def Init(self, workerCtxGroup=None, workerCount=None):
        if workerCtxGroup is None:
            workerCtxGroup = JobManager.DEFAULT_CTXGROUP_ID
        if workerCount is None:
            workerCount = multiprocessing.cpu_count()
            
        if self.__jobCtxGroups.has_key(workerCtxGroup):
            raise RuntimeError("group already initialized")
        
        workers = []
        i = 0
        while i < workerCount:
            self.__logger.debug("creating worker for group %s", workerCtxGroup)
            worker = Worker(self, workerCtxGroup, i)
            workers.append(worker)
                            
            i += 1

        jcGroup = _JobCtxGroup(workerCtxGroup, workers)
        self.__jobCtxGroups[workerCtxGroup] = jcGroup
            
        for worker in workers:
            worker.start()

            
    def EnqueueContext(self, jobContext):
        assert isinstance(threading.current_thread(), threading._MainThread)
        
        if not self.__jobCtxGroups.has_key(jobContext.GetGroupId()):
            raise RuntimeError("job group %s not available" % jobContext.GetGroupId()) 

        self.__logger.debug("%s: register job", jobContext)
        
        self.__jobCtxGroups[jobContext.GetGroupId()].Put(jobContext)
        
        for visual in self.__visuals:
            visual.RegisterJob(jobContext)
            
    def __TransferIdle2Active(self, jcGroup):
        with jcGroup.ActiveLock():
            jcIdle = jcGroup.Get()
            if self.__StartCtx(jcIdle):
                jobCtxActive = jcIdle
                jcGroup.SetActive(jobCtxActive)
                return jobCtxActive

    def _GetWorkLoad(self, workerCtxGroup, block=True, timeout=None):
        jcGroup = self.__jobCtxGroups[workerCtxGroup]
        
        with jcGroup.ActiveLock():
            jobCtxActive = jcGroup.Active()
        while jobCtxActive is None:
            # no context active, get one from idle queue
            try:
                jobCtxActive = self.__TransferIdle2Active(jcGroup)
            except Queue.Empty:
                jcGroup.Wait(timeout)
                jobCtxActive = self.__TransferIdle2Active(jcGroup)
        
        jobCtxActive = jcGroup.Active()
        try:
            return jobCtxActive, jobCtxActive.GetWorkLoad(False, None) # FIXME: no tuple
        except Queue.Empty:
            # no more workloads, job done, only __FinishCtx() needs to be done
            
            with jcGroup.ActiveLock():
                # wait for all workers to be done (better use WaitForMultipleObjects) 
                while not self.__destroying:
                    result = True
                    for worker in jcGroup.Workers(): 
                        if worker.GetContextGroupId() == workerCtxGroup:
                            result = result and not worker.IsBusy()
                    if result:
                        break
                    else:
                        time.sleep(0.5)
                
                jobCtxActive = jcGroup.Active()
                if jobCtxActive is not None:
                    jcGroup.SetActive(None)
                    self.__FinishCtx(jobCtxActive)
            
            raise Queue.Empty()

    def __StartCtx(self, ctx):
        self.__logger.debug("starting %s...", ctx.GetName())
        try:
            ctx._Begin() # IGNORE:W0212
        except JobAbortedException:
            return False    
        except:
            self.__logger.error("not started %s", # IGNORE:W0702
                                ctx.GetName(), exc_info=1) 
            return False            

        self.__logger.debug("started %s", ctx.GetName())
        return True
    
    def __FinishCtx(self, ctx):
        self.__logger.debug("finalizing %s...", ctx.GetName())
        try:
            ctx._Done() # IGNORE:W0212
        except:
            self.__logger.error("error %s", # IGNORE:W0702
                                ctx.GetName(), exc_info=1)
        finally:
            self.__logger.debug("finished %s", ctx.GetName())
            
    def Destroy(self):
        self.__logger.debug("start destroying")
        self.__destroying = True
        for jcGroup in self.__jobCtxGroups.values():
            for worker in jcGroup.Workers():
                worker.Kill()

            jcGroup.Notify()
        
            for worker in jcGroup.Workers():
                self.__logger.debug("joining worker %s", worker.getName())
                worker.join(3)
                if worker.isAlive():
                    self.__logger.warning("could not join worker %s", worker.getName())

        self.__logger.debug("destroyed")

