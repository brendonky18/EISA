from typing import Callable, Any, List, Optional
from threading import Thread, Lock
from time import sleep
from dataclasses import dataclass

@dataclass
class ClockEvent:
    delay: int = 0
    callback: Callable[[], None] = lambda: None

class Clock:
    cycle_count: int = 0
    
    run_clock: bool = False
    run_clock_lock: Lock = Lock()

    pending_calls: list[ClockEvent] = []
    pending_calls_lock: Lock = Lock()

    clock_thread = None

    @classmethod
    def start(cls):
        """class method to start the program clock

        Raises
        ------
        RuntimeError
            [description]
        """
        if cls.run_clock:
            raise RuntimeError('Cannot have multiple instances of clock running')
        else:
            cls.run_clock = True
            def run():
                cls.run_clock_lock.acquire()
                while cls.run_clock:
                    cls.run_clock_lock.release()

                    with cls.pending_calls_lock:
                        for cur_event in cls.pending_calls: # iterate over and update all events
                            if cur_event.delay == 0:    
                                cur_event.callback()        # trigger the event's callback
                                print('callback triggered')
                                               
                            cur_event.delay -= 1            # decrement event delay
                            print('decrement')
                        print('loop')
                        
                        # remove events that have been called
                        cls.pending_calls = [cur_event for cur_event in cls.pending_calls if cur_event.delay >= 0]
                    
                    sleep(0.1)

                    cls.run_clock_lock.acquire()            # get the lock for the next iteration
                cls.run_clock_lock.release()                # release the lock when finished
        
            cls.clock_thread = Thread(target=run)
            cls.clock_thread.start()                        # actually start running the thread
            print('clock thread started')
            
    @classmethod
    def stop(cls):
        """class method to stop the program clock
        """
        with cls.run_clock_lock:
            cls.run_clock = False
        cls.clock_thread.join()


    def wait(self, delay: int, wait_event: Callable[..., Any], wait_event_args: Optional[List[Any]] = None) -> None:
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
        self._waiting = True

        def on_done():
            self._waiting = False

            print(f'updated waiting: {self._waiting}') # debug

        # add to the list of events
        with Clock.pending_calls_lock:
            Clock.pending_calls.append(ClockEvent(delay=delay, callback=on_done))
        
        # wait for it
        while self._waiting:
            sleep(0.01)

        if wait_event_args == None:
            return wait_event()
        else:
            return wait_event(*wait_event_args) # type: ignore
            # not sure how to get around that error, something with the ellipsis when defining the wait_event's type