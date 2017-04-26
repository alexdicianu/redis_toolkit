import time
import curses
import sys
from collections import defaultdict, Counter

# Only insterested in GET/SET for now.
operations = ['GET', 'SET']

def reset(screen):
    curses.nocbreak()
    screen.keypad(0)
    curses.echo()
    curses.endwin()

def print_hitrate(window):
    try:
        #output = get_header()
        #window.addstr(output)
        while 1:
            output = parse_input()
            if output:
                window.addstr(output)
                window.refresh()
                time.sleep(0.1)
        reset(window)
    except KeyboardInterrupt:
        reset(window)
        exit()

def get_header():
    output = ''
    output += str('{:<128}'.format('Key'))
    output += str('{:<18}'.format('Hit_Rate'))
    for op in operations:
        output += str('{:<8}'.format(op))
    output += str("\n")
    return output

def parse_input():
    output = 'a   b   c'
    output += "\n"
    return output
    
if __name__ == '__main__':
    curses.wrapper(print_hitrate)
