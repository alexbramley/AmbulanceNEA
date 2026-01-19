import math

class Vector2(object):
    """2 dimensional vector class"""
    def __repr__(self):
        return f"Vector2({self.x}, {self.y})"
    
    def __init__(self, x:float, y:float):
        self.x = x
        self.y = y
    
    @staticmethod
    def Add(operand1, operand2):
        """Adds two vectors"""
        return Vector2(operand1.x + operand2.x, operand1.y + operand2.y)
    
    @staticmethod
    def Multiply(vector_operand, float_operand):
        """Multiplies a vector by a scalar"""
        return Vector2(vector_operand.x * float_operand, vector_operand.y * float_operand)
    
    @staticmethod
    def Magnitude(vector_operand):
        """Returns the magnitude of a vector"""
        return math.sqrt((vector_operand.x * vector_operand.x) + (vector_operand.y * vector_operand.y))
    
    @staticmethod
    def Normalise(vector_operand):
        """Returns the vector in a normalised form"""
        magnitude = Vector2.Magnitude(vector_operand)
        return Vector2(vector_operand.x / magnitude, vector_operand.y / magnitude)
    