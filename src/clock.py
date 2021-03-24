from typing import Callable, Any, List, Optional, Type
from threading import Thread, Lock
from time import sleep, perf_counter_ns
from dataclasses import dataclass

@dataclass
class ClockEvent:
    delay: int = 0
    counter: int = 0
    callback: Callable[[], None] = lambda: None

class Clock:
    cycle_count: int = 0
    
    run_clock: bool = False
    run_clock_lock: Lock = Lock()

    pending_calls: list[ClockEvent] = []
    pending_calls_lock: Lock = Lock()

    step_clock: bool = False
    step_clock_counter: int = 0
    step_clock_lock: Lock = Lock()

    clock_thread = None

    @classmethod
    def start(cls):
        """class method to start the program clock

        Raises
        ------
        RuntimeError
            [description]
        """
        if cls.run_clock or cls.step_clock:
            raise RuntimeError('Cannot have multiple instances of clock running')
        else:
            cls.run_clock = True
            def run():
                cls.run_clock_lock.acquire()                # get the lock before entering
                while cls.run_clock:
                    cls.run_clock_lock.release()

                    with cls.pending_calls_lock:
                        for cur_event in cls.pending_calls: # iterate over and update all events
                            cur_event.counter += 1
                            
                            if cur_event.delay == cur_event.counter:    
                                cur_event.callback()        # trigger the event's callback         
                                                        
                        # remove events that have been called
                        cls.pending_calls = [cur_event for cur_event in cls.pending_calls if cur_event.counter < cur_event.delay]

                    cls.run_clock_lock.acquire()            # get the locks for the next iteration
                cls.run_clock_lock.release()                # releases the lock when finished
        
            cls.clock_thread = Thread(target=run, name='Clock Running')
            cls.clock_thread.start()                        # actually start running the thread
            
    @classmethod
    def stop(cls):
        """class method to stop the program clock
        """
        with cls.run_clock_lock:
            cls.run_clock = False
        cls.clock_thread.join()
    
    @classmethod
    def step(cls, count: int=1):
        if cls.run_clock or cls.step_clock:
            raise RuntimeError('Cannot have multiple instances of clock running')
        else:
            cls.step_clock = True
            def run():
                cls.step_clock_lock.acquire()                # get the lock before entering
                for step in range(count):
                    cls.step_clock_lock.release()

                    with cls.pending_calls_lock:
                        for cur_event in cls.pending_calls: # iterate over and update all events
                            cur_event.counter += 1
                            
                            if cur_event.delay == cur_event.counter:    
                                cur_event.callback()        # trigger the event's callback         
                                                        
                        # remove events that have been called
                        cls.pending_calls = [cur_event for cur_event in cls.pending_calls if cur_event.counter < cur_event.delay]

                    cls.step_clock_lock.acquire()            # get the locks for the next iteration
                cls.step_clock_lock.release()                # releases the lock when finished
        
            cls.clock_thread = Thread(target=run, name='Clock Stepping')
            cls.clock_thread.start()                        # actually start running the thread
            cls.clock_thread.join()
            cls.step_clock = False

        

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
        if not (Clock.run_clock or Clock.step_clock):
            from __main__ import terminal_print
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

        from __main__ import terminal_print
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
        