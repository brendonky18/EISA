from dataclasses import dataclass
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, Future
from time import sleep
from typing import Callable, Any, List, Optional, Type
from types import TracebackType


@dataclass
class ClockEvent:
    delay: int = 0
    counter: int = 0
    callback: Callable[[], None] = lambda: None
    name: Optional[str] = None

    def __str__(self) -> str:
        s = ''
        if self.name is not None:
            s += f'{self.name}: '
        else:
            s += f'Event: ,'

        s += f'Total Delay: {self.delay}, Cycles Passed: {self.counter}'

        return s

class Clock:
    # region variables
    pending_calls: list[ClockEvent] = []
    pending_calls_lock: Lock = Lock()

    step_clock_counter: int = 0

    run_clock: bool = False

    clock_thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix='clock')
    clock_thread_task: Future = None # type: ignore
    clock_tread_lock: Lock = Lock()
    # endregion variables

    @classmethod
    def start(cls):
        """class method to start the program clock

        Raises
        ------
        RuntimeError
            [description]
        """
        def run():
            while Clock.run_clock:
                cls.resolve_pending_calls()

        with Clock.clock_tread_lock:
            # checks if there is a clock thread already running
            if cls.clock_thread_task is None or cls.clock_thread_task.done():
                Clock.run_clock = True
                cls.clock_thread_task = cls.clock_thread.submit(run)
            else:
                raise RuntimeError('Cannot have multiple instances of clock running')
            
    @classmethod
    def stop(cls):
        """class method to stop the program clock
        """
        Clock.run_clock = False

        # checks if there was an error
        clock_thread_exception = cls.clock_thread_task.exception()
        if clock_thread_exception is not None:
            raise clock_thread_exception
    
    @classmethod
    def step(cls, count: int=1):
        def run():
            for step in range(count):
                cls.resolve_pending_calls()
        with Clock.clock_tread_lock:
            # checks if there is a clock thread already running
            if cls.clock_thread_task is None or cls.clock_thread_task.done():        
                # checks for an exception in the previous execution     
                clock_thread_exception =  cls.clock_thread_task.exception()
                if clock_thread_exception is not None:
                    raise clock_thread_exception
                else:
                    Clock.run_clock = True
                    cls.clock_thread_task = cls.clock_thread.submit(run)
            else:
                raise RuntimeError('Cannot have multiple instances of clock running')

        # wait for the function to be done
        while not cls.clock_thread_task.done():
            pass

        # checks if there was an error
        clock_thread_exception = cls.clock_thread_task.exception()
        if clock_thread_exception is not None:
            raise clock_thread_exception

    @classmethod
    def resolve_pending_calls(cls):
        with cls.pending_calls_lock:
            # print('a')
            for cur_event in cls.pending_calls: # iterate over and update all events
                cur_event.counter += 1
                
                if cur_event.delay == cur_event.counter:    
                    cur_event.callback()        # trigger the event's callback         
                                            
            # remove events that have been called
            cls.pending_calls = [cur_event for cur_event in cls.pending_calls if cur_event.counter < cur_event.delay]

    def __enter__(self):
        if Clock.clock_thread._shutdown:
            Clock.clock_thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix='clock')
        
        Clock.start()
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType]
        ):
        Clock.stop()
        print('clock stopped')
        Clock.clock_thread.shutdown(wait=True)

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
            terminal_print(f'Warning: Clock not running. {wait_event_name} will not be executed')
            
        self._waiting = True
        result = None
        def on_done():
            self._waiting = False
            
            # trigger the passed vallback
            if wait_event is not None:
                result =  wait_event() if wait_event_args is None else wait_event(*wait_event_args)

            # print that the function has completed
            terminal_print(f'{"Command" if wait_event_name is None else wait_event_name} took {my_event.counter} cycle{"s" if my_event.counter > 1 else ""} to complete')

        # add to the list of events
        my_event = ClockEvent(delay=delay, counter=0, callback=on_done, name=wait_event_name)
        with Clock.pending_calls_lock:
            Clock.pending_calls.append(my_event)
        
        # wait for it
        while self._waiting:
            sleep(0.001)

        return result

        