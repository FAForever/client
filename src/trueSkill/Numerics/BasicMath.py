



# Basic math functions.

def square(x):
    '''
     Squares the input (x^2 = x * x)
      @param number $x Value to square (x)
     @return number The squared value (x^2)
    '''
    
    return x**2

def sumArray(itemsToSum, callback ) :
    '''
     Sums the items in $itemsToSum
     @param array $itemsToSum The items to sum,
     @param callback $callback The function to apply to each array element before summing.
     @return number The sum.
'''
    
    mappedItems = map(callback, itemsToSum)
    return sum(mappedItems)

