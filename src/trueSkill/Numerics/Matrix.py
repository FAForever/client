#-------------------------------------------------------------------------------
# Copyright (c) 2012 Gael Honorez.
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the GNU Public License v3.0
# which accompanies this distribution, and is available at
# http://www.gnu.org/licenses/gpl.html
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#-------------------------------------------------------------------------------





from math import fabs, sqrt

ERROR_TOLERANCE = 0.0000000001

def make_list(size):
    """create a list of size number of zeros"""
    mylist = []
    for i in range(size):
        mylist.append(0)
    return mylist

def make_matrix(rows, cols):
    """
     Create a 2D >matrix as a list of rows number of lists
    where the lists are cols in size
    resulting matrix contains zeros
    """
    matrix= []
    for i in range(rows):
        matrix.append(make_list(cols))
    return matrix

class Matrix(object):
    
    def __init__(self, rows =0 , columns = 0, matrixData = None) :
        self._matrixRowData = []

        self._rowCount = rows
        self._columnCount = columns
        if matrixData == None :
            self._matrixRowData = make_matrix(rows, columns)
        else :
            self._matrixRowData = make_matrix(rows, columns)
            self._matrixRowData = matrixData

        
    @staticmethod
    def fromColumnValues(rows, columns, columnValues) :

        result = Matrix(rows, columns)

        for currentColumn in range(columns) :
            currentColumnData = columnValues[currentColumn]
            
            for currentRow in range(rows) :
                result.setValue(currentRow, currentColumn, currentColumnData[currentRow])

        return result
    
    
    @staticmethod
    def fromRowsColumns(*args, **kwargs) :
        rows = args[0]
        cols = args[1]
        
        result =  Matrix(rows, cols)
        currentIndex = 2

        for currentRow in range(rows) :
            for currentColumn in range(cols) :
                currentIndex = currentIndex + 1
                
                result.setValue(currentRow, currentColumn, args[currentIndex])
        return result

    def getRowCount(self) :
        return self._rowCount

    def getColumnCount(self) :
        return self._columnCount

    def getValue(self, row, col) :
        return self._matrixRowData[row][col]

    def setValue(self, row, col, value) :
        
        self._matrixRowData[row][col] = value

 
    def getTranspose(self) :
        # Just flip everything
        transposeMatrix = make_matrix(self._columnCount, self._rowCount)

        rowMatrixData = self._matrixRowData

        
        for currentRowTransposeMatrix in range(self._columnCount) :
        
            for currentColumnTransposeMatrix in range (self._rowCount) :
            
                transposeMatrix[currentRowTransposeMatrix][currentColumnTransposeMatrix] = rowMatrixData[currentColumnTransposeMatrix][currentRowTransposeMatrix]

        return Matrix(self._columnCount, self._rowCount, transposeMatrix)


    def __isSquare(self) :
        if (self._rowCount == self._columnCount) and (self._rowCount > 0) :
            return 1
        return 0

    def getDeterminant(self) :
        # Basic argument checking

        if not self.__isSquare() :
            raise Exception("Matrix must be square!")


        if (self._rowCount == 1) :
            # Really happy path :)
            return self._matrixRowData[0][0]


        if (self._rowCount == 2) :

#             Happy path!
#             Given:
#             | a b |
#             | c d |
#             The determinant is ad - bc
            a = self._matrixRowData[0][0]
            b = self._matrixRowData[0][1]
            c = self._matrixRowData[1][0]
            d = self._matrixRowData[1][1]
            return a*d - b*c


#         I use the Laplace expansion here since it's straightforward to implement.
#         It's O(n^2) and my implementation is especially poor performing, but the
#         core idea is there. Perhaps I should replace it with a better algorithm
#         later.
#         See http://en.wikipedia.org/wiki/Laplace_expansion for details

        result = 0.0

        # I expand along the first row
        for currentColumn in range(self._columnCount) :
            firstRowColValue = self._matrixRowData[0][currentColumn]
            cofactor = self.getCofactor(0, currentColumn)
            itemToAdd = firstRowColValue*cofactor
            result = result + itemToAdd

        return result


    def getAdjugate(self) :
        
        if not self.__isSquare() :
            raise Exception("Matrix must be square!")

        # See http://en.wikipedia.org/wiki/Adjugate_matrix
        if (self._rowCount == 2) :
#             Happy path!
#             Adjugate of:
#             | a b |
#             | c d |
#             is
#             | d -b |
#             | -c a |

            a = self._matrixRowData[0][0]
            b = self._matrixRowData[0][1]
            c = self._matrixRowData[1][0]
            d = self._matrixRowData[1][1]

            return SquareMatrix( d, -b, -c,  a)


        # The idea is that it's the transpose of the cofactors
        result = make_matrix(self._columnCount, self._rowCount)

        for currentColumn in range(self._columnCount) :
            for currentRow in range(self._rowCount) :

                result[currentColumn][currentRow] = self.getCofactor(currentRow, currentColumn)


        return Matrix(self._columnCount, self._rowCount, result)


    def getInverse(self) :

        if self._rowCount == 1 and self._columnCount == 1 :
            return SquareMatrix(1.0/self._matrixRowData[0][0])


        # Take the simple approach:
        # http://en.wikipedia.org/wiki/Cramer%27s_rule#Finding_inverse_matrix
        determinantInverse = 1.0 / self.getDeterminant()
        adjugate = self.getAdjugate()

        return self.scalarMultiply(determinantInverse, adjugate)

    @staticmethod
    def scalarMultiply(scalarValue, matrix) :

        rows = matrix.getRowCount()
        columns = matrix.getColumnCount()
        newValues = make_matrix(rows, columns)

        for currentRow in range(rows) :
            for currentColumn in range(columns) :
                newValues[currentRow][currentColumn] = scalarValue*matrix.getValue(currentRow, currentColumn)

        return Matrix(rows, columns, newValues)


    @staticmethod
    def add(left, right) :
        if ((left.getRowCount() != right.getRowCount()) or (left.getColumnCount() != right.getColumnCount())) :

            raise Exception("Matrices must be of the same size");


        #simple addition of each item

        resultMatrix = make_matrix(left.getRowCount(), right.getColumnCount())

        for currentRow in range(left.getRowCount()) :
            for currentColumn in range (right.getColumnCount()) :
                resultMatrix[currentRow][currentColumn] = left.getValue(currentRow, currentColumn) + right.getValue(currentRow, currentColumn)


        return Matrix(left.getRowCount(), right.getColumnCount(), resultMatrix)
    
    @staticmethod
    def multiply(left, right) :
        '''
        Just your standard matrix multiplication.
        See http://en.wikipedia.org/wiki/Matrix_multiplication for details
        '''

        if (left.getColumnCount() != right.getRowCount()) :
            raise Exception("The width of the left matrix must match the height of the right matrix");


        resultRows = left.getRowCount()
        resultColumns = right.getColumnCount()

        resultMatrix = make_matrix(resultRows, resultColumns)


        for currentRow in range (resultRows) :
            for currentColumn in range(resultColumns) :
                productValue = 0
                
                for vectorIndex in range(left.getColumnCount()) :

                    leftValue = left.getValue(currentRow, vectorIndex)
                    rightValue = right.getValue(vectorIndex, currentColumn)
                    vectorIndexProduct = leftValue*rightValue
                    productValue = productValue + vectorIndexProduct


                resultMatrix[currentRow][currentColumn] = productValue


        return Matrix(resultRows, resultColumns, resultMatrix)
  
    def getMinorMatrix(self, rowToRemove, columnToRemove) :

#         See http://en.wikipedia.org/wiki/Minor_(linear_algebra)
#         Im going to use a horribly naive algorithm... because I can :)

        
        result = []
        actualRow = 0

        for currentRow in range(self._rowCount) :

            if (currentRow == rowToRemove) :
                continue
            
            actualCol = 0
            result.insert(actualRow,[])
            
            for currentColumn in range(self._columnCount) :

                result[actualRow].insert(actualCol,0)
                if (currentColumn == columnToRemove) :
                    continue
              
                
                result[actualRow][actualCol] = self._matrixRowData[currentRow][currentColumn]

                actualCol = actualCol + 1

            actualRow = actualRow + 1 

        return Matrix(self._rowCount - 1, self._columnCount - 1, result)


    def getCofactor(self, rowToRemove, columnToRemove) :
        '''
         See http://en.wikipedia.org/wiki/Cofactor_(linear_algebra) for details
         REVIEW: should things be reversed since I'm 0 indexed?
        '''
        
        sum = rowToRemove + columnToRemove

        isEven = (sum%2 == 0)

        if isEven :
            return self.getMinorMatrix(rowToRemove, columnToRemove).getDeterminant()
        else :
            return -1.0*self.getMinorMatrix(rowToRemove, columnToRemove).getDeterminant()

    def equals(self, otherMatrix) :

        # If one is null, but not both, return false.
        if (otherMatrix == None) :
            return False


        if ((self._rowCount != otherMatrix.getRowCount()) or (self._columnCount != otherMatrix.getColumnCount())) :
            return False


        for currentRow in range(self._rowCount) :
            for currentColumn in range(self._columnCount) :
            
                delta = fabs(self._matrixRowData[currentRow][currentColumn] -otherMatrix.getValue(currentRow, currentColumn))

                if (delta > self.ERROR_TOLERANCE) :
                    return False
        return True
    
    def __str__(self) :
        msg = ''

        for row in range(self._rowCount) :
#            for col in range(self._columnCount) :
            msg += str(self._matrixRowData[row]) + '\n'
        return msg
    
    
class Vector(Matrix) :
    def __init__(self, vectorValues):
        columnValues =[]
       
        for currentVectorValue in vectorValues :
            list = []
            list.append(currentVectorValue)
            columnValues.append(list)

        super(Vector, self).__init__(len(vectorValues), 1, columnValues)
        

class SquareMatrix(Matrix) :
    def __init__(self, *args, **kwargs):
        allValues = args
        
        
        rows = int(sqrt(len(allValues)))
        cols = rows

        matrixData = make_matrix(rows, cols)
        allValuesIndex = 0
        
        for currentRow in range(rows) :
            for currentColumn in range(cols) :
  
                matrixData[currentRow][currentColumn] = allValues[allValuesIndex]
                allValuesIndex  = allValuesIndex + 1
                
        super(SquareMatrix, self).__init__(rows, cols, matrixData)        
        
        
class DiagonalMatrix(Matrix) :
    def __init__(self, diagonalValues):
    
        diagonalCount = len(diagonalValues)
        rowCount = diagonalCount
        colCount = rowCount
        
        super(DiagonalMatrix, self).__init__(rowCount, colCount)   
        
        for currentRow in range (rowCount) :
            for currentCol in range(colCount) :

                if currentRow == currentCol :
                    self.setValue(currentRow, currentCol, diagonalValues[currentRow])
                else :
                    self.setValue(currentRow, currentCol, int(0))


class IdentityMatrix(DiagonalMatrix) :
    def __init__(self, rows):
        super(IdentityMatrix, self).__init__([1]*4)

