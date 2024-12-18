from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import math

# ----------------------------------------------------------------------------------------------------------------
# Calculator Component
# ----------------------------------------------------------------------------------------------------------------
# Simple class to make complicated calculations
# Used by the $calc command
# ----------------------------------------------------------------------------------------------------------------

class Calc():
    FUNCS : list[str] = ['cos', 'sin', 'tan', 'acos', 'asin', 'atan', 'cosh', 'sinh', 'tanh', 'acosh', 'asinh', 'atanh', 'exp', 'ceil', 'abs', 'factorial', 'floor', 'round', 'trunc', 'log', 'log2', 'log10', 'sqrt', 'rad', 'deg'] # supported functions

    def __init__(self : Calc, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.expression : str = ""
        self.index : int = 0
        self.vars : dict[str, float] = {}

    def init(self : Calc) -> None:
        pass

    """reset()
    Reinitialize the calculator state
    """
    def reset(self : Calc) -> None:
        self.expression = ""
        self.index = 0
        self.vars = {
            'pi' : math.pi,
            'e' : math.e
        }

    """evaluate()
    Evaluate a mathematical expression and return the result
    
    Parameters
    ----------
    expression: Math expression
    vars: Variable
    
    Raises
    ------
    Exception: For any errors
    
    Returns
    --------
    float or int: Result
    """
    def evaluate(self : Calc, expression : str = "", vars : dict = {}) -> int|float:
        # start by resetting calculator
        self.reset()
        # prepare expression
        self.expression = expression.replace(' ', '').replace('\t', '').replace('\n', '').replace('\r', '')
        # store variables
        self.vars = self.vars | vars
        for func in self.FUNCS: # check variable names for dupes with function names
            if func in self.vars: raise Exception("Variable name '{}' can't be used".format(func))
        # parse expression and get the result
        value : float = float(self.parse())
        # interruption check
        if self.isNotDone():
            raise Exception("Unexpected character '{}' found at index {}".format(self.peek(), self.index))
        # adjust float if needed and convert to int
        epsilon : float = 0.0000000001
        if int(value) == value:
            return int(value)
        elif int(value + epsilon) != int(value):
            return int(value + epsilon)
        elif int(value - epsilon) != int(value):
            return int(value)
        return value

    """isNotDone()
    Return True if the evaluation isn't finished
    
    Returns
    --------
    bool: True if the evaluation isn't finished, False if it is
    """
    def isNotDone(self : Calc) -> bool:
        return self.index < len(self.expression)

    """peek()
    Get the next element
    
    Returns
    --------
    str: Next element to be parsed
    """
    def peek(self : Calc) -> str:
        return self.expression[self.index:self.index + 1]

    """parse()
    Parse the next elements
    
    Returns
    --------
    float or int: Result
    """
    def parse(self : Calc) -> int|float:
        values : list[float] = [self.multiply()] # start by calling multiply
        while True:
            c : str = self.peek() # get next character
            if c in ['+', '-']: # as long as it's a + or - operator
                self.index += 1
                if c == '-': values.append(- self.multiply()) # if -, minus multiply
                else: values.append(self.multiply()) # else just multiply
            else:
                break
        return sum(values) # addition all values

    """multiply()
    Multiply the next elements
    
    Returns
    --------
    float or int: Result
    """
    def multiply(self : Calc) -> int|float:
        values : list[float] = [self.parenthesis()] # call parenthesis first
        denominator : int|float 
        while True:
            c : str = self.peek() # check operator
            if c in ['*', 'x']: # multiply
                self.index += 1
                values.append(self.parenthesis())
            elif c == '/': # divie
                div_index = self.index
                self.index += 1
                denominator = self.parenthesis()
                if denominator == 0:
                    raise Exception("Division by 0 occured at index {}".format(div_index))
                values.append(1.0 / denominator)
            elif c == '%': # modulo
                mod_index = self.index
                self.index += 1
                denominator = self.parenthesis()
                if denominator == 0:
                    raise Exception("Modulo by 0 occured at index {}".format(mod_index))
                values[-1] = values[-1] % denominator
            elif c == '^': # exponent
                self.index += 1
                exponent : int|float = self.parenthesis()
                values[-1] = values[-1] ** exponent
            elif c == '!': # factorial
                self.index += 1
                values[-1] = math.factorial(values[-1])
            else:
                break
        value : float = 1.0
        factor : float
        for factor in values:
            value *= factor
        return value

    """parenthesis()
    Parse the elements in the parenthesis
    
    Raises
    ------
    Exception: Missing parenthesis
    
    Returns
    --------
    float or int: Result
    """
    def parenthesis(self : Calc) -> int|float:
        if self.peek() == '(': # check if next character is an open parenthesis
            self.index += 1
            value : int|float = self.parse() # then parse inside that parenthesis
            if self.peek() != ')': # we expect the parenthesis to be closed after
                raise Exception("No closing parenthesis foundat position {}".format(self.index))
            self.index += 1
            return value # return result
        else:
            return self.negative() # call negative, will return the next value

    """negative()
    Get the negative of the value
    
    Returns
    --------
    float or int: Result
    """
    def negative(self : Calc) -> int|float:
        if self.peek() == '-': # if minus, multiply next value with -1
            self.index += 1
            return -1 * self.parenthesis()
        else: # else return next value
            return self.value()

    """value()
    Get the value of the next element
    
    Returns
    --------
    float or int: Result
    """
    def value(self : Calc) -> int|float:
        if self.peek() in '0123456789.': # check if digit or dot
            return self.number()
        else: # else expect variable or function
            return self.variable_or_function()

    """variable_or_function()
    Get the result of a variable or a function
    
    Raises
    ------
    Exception: Error during the parsing
    
    Returns
    --------
    float or int: Result
    """
    def variable_or_function(self : Calc) -> int|float:
        var : str = ''
        while self.isNotDone(): # retrieve var/func name
            c : str = self.peek()
            if c.lower() in '_abcdefghijklmnopqrstuvwxyz0123456789':
                var += c
                self.index += 1
            else:
                break
        
        value : float|None = self.vars.get(var, None) # check if variable
        if value == None: # it's not
            # check if function
            if var not in self.FUNCS:
                raise Exception("Unrecognized variable '{}'".format(var))
            else:
                # parse func parameter
                param : int|float = self.parenthesis()
                match var: # call function for that parameter
                    case 'cos': value = math.cos(param)
                    case 'sin': value = math.sin(param)
                    case 'tan': value = math.tan(param)
                    case 'acos': value = math.acos(param)
                    case 'asin': value = math.asin(param)
                    case 'atan': value = math.atan(param)
                    case 'cosh': value = math.cosh(param)
                    case 'sinh': value = math.sinh(param)
                    case 'tanh': value = math.tanh(param)
                    case 'acosh': value = math.acosh(param)
                    case 'asinh': value = math.asinh(param)
                    case 'atanh': value = math.atanh(param)
                    case 'exp': value = math.exp(param)
                    case 'ceil': value = math.ceil(param)
                    case 'floor': value = math.floor(param)
                    case 'round': value = math.floor(param)
                    case 'abs': value = math.fabs(param)
                    case 'trunc': value = math.trunc(param)
                    case 'log':
                        if param <= 0: raise Exception("Can't evaluate the logarithm of '{}'".format(param))
                        value = math.log(param)
                    case 'log2':
                        if param <= 0: raise Exception("Can't evaluate the logarithm of '{}'".format(param))
                        value = math.log2(param)
                    case 'log10':
                        if param <= 0: raise Exception("Can't evaluate the logarithm of '{}'".format(param))
                        value = math.log10(param)
                    case 'sqrt': value = math.sqrt(param)
                    case 'rad': value = math.radians(param)
                    case 'deg': value = math.degrees(param)
                    case _: raise Exception("Unrecognized function '{}'".format(var))
        # return result
        return float(value)

    """number()
    Return a numerical value
    
    Raises
    ------
    Exception: Error during the parsing
    
    Returns
    --------
    float or int: Result
    """
    def number(self : Calc) -> int|float:
        strValue : list[str] = []
        decimal_found : bool = False
        c : str = ''
        # read number
        while self.isNotDone():
            c = self.peek()
            if c == '.':
                if decimal_found:
                    raise Exception("Found an extra period in a numberat position {}".format(self.index))
                decimal_found = True
                strValue.append('.')
            elif c in '0123456789':
                strValue.append(c)
            else:
                break
            self.index += 1
        # error check
        if len(strValue) == 0:
            if c == '': raise Exception("Unexpected end found\nDid you perhaps forget a bracket?\nExample: `log(20)` not `log 20`")
            else: raise Exception("Unexpected end found\nA value was expectedat position {}".format(self.index))
        return float("".join(strValue))