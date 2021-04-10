from dataclasses import dataclass
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, Future
from time import sleep
from typing import Callable, Any, List, Optional


@dataclass
class ClockEvent:
    delay: int = 0
    counter: int = 0
    callback: Callable[[], None] = lambda: None


class Clock:
    pending_calls: list[ClockEvent] = []
    pending_calls_lock: Lock = Lock()

    step_clock_counter: int = 0

    run_clock: bool = False

    clock_thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix='clock')
    clock_thread_task: Future = None # type: ignore

    @classmethod
    def start(cls):
        """class method to start the program clock

        Raises
        ------
        RuntimeError
            [description]
        """
        if cls.clock_thread_task is None or cls.clock_thread_task.done():
            def run():
                while Clock.run_clock:
                    cls.resolve_pending_calls()
        
            Clock.run_clock = True
            cls.clock_thread_task = cls.clock_thread.submit(run)
        else:
            raise RuntimeError('Cannot have multiple instances of clock running')
            
    @classmethod
    def stop(cls):
        """class method to stop the program clock
        """
        Clock.run_clock = False
        # cls.clock_thread.shutdown(wait=True)
    
    @classmethod
    def step(cls, count: int=1):
        if cls.clock_thread_task is None or cls.clock_thread_task.done():
            def run():
                for step in range(count):
                    cls.resolve_pending_calls()
        
            cls.clock_thread_task = cls.clock_thread.submit(run)
            # cls.clock_thread.shutdown(wait=True)
        else:
            raise RuntimeError('Cannot have multiple instances of clock running')

    @classmethod
    def resolve_pending_calls(cls):
        with cls.pending_calls_lock:
            for cur_event in cls.pending_calls: # iterate over and update all events
                cur_event.counter += 1
                
                if cur_event.delay == cur_event.counter:    
                    cur_event.callback()        # trigger the event's callback         
                                            
            # remove events that have been called
            cls.pending_calls = [cur_event for cur_event in cls.pending_calls if cur_event.counter < cur_event.delay]

    def wait(
        self, 
        delay: int, 
        wait_event: Optional[Callable[..., Any]] = None, 
        wait_event_args: Optional[List[Any]] = None,
        wait_event_name: Optional[str] = None
    ) -> None:
        """instance function which will wait the specified amount of time and then invoke the passed function
        
        requires an instance of Clock to be called for each thread
        
        Parameters
        ----------
        delay : int
            the number of clock cycles to wait for
        wait_event : function
            the function to be called

        Returns
        -------
        Any
            returns whatever the passed function returns
        """
        from debug import terminal_print
        if Clock.clock_thread_task is None or Clock.clock_thread_task.done():
            terminal_print('Warning: Clock not running. Commands will not be executed')
            
        self._waiting = True

        def on_done():
            self._waiting = False

        # add to the list of events
        my_event = ClockEvent(delay=delay, counter=0, callback=on_done)
        with Clock.pending_calls_lock:
            Clock.pending_calls.append(my_event)
        
        # wait for it
        while self._waiting:
            sleep(0.001)

        #from __main__ import terminal_print
        terminal_print(f'{"Command" if wait_event_name is None else wait_event_name} took {my_event.counter} cycle{"s" if my_event.counter > 1 else ""} to complete')

        # trigger the event function if one was passes
        if wait_event is not None:
            if wait_event_args is None:
                return wait_event()
            else:
                return wait_event(*wait_event_args) # type: ignore
                # not sure how to get around that error, something with the ellipsis when defining the wait_event's type
        else:
            return None
        