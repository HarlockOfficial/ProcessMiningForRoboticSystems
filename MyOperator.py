from enum import Enum
import pm4py


class MyOperator(Enum):
    # sequence operator
    SEQUENCE = '->'
    # exclusive choice operator
    XOR = 'X'
    # parallel operator
    PARALLEL = '+'
    # loop operator
    LOOP = '*'
    # or operator
    OR = 'O'
    # interleaving operator
    INTERLEAVING = "<>"

    RECEIVE_MESSAGE = "receive_message"

    def __str__(self):
        """
        Provides a string representation of the current operator

        Returns
        -----------
        stri
            String representation of the process tree
        """
        return self.value

    def __repr__(self):
        """
        Provides a string representation of the current operator

        Returns
        -----------
        stri
            String representation of the process tree
        """
        return self.value


pm4py.objects.process_tree.obj.Operator = MyOperator
