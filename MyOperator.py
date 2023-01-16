from enum import Enum
import pm4py


class MyOperator(Enum):
    from pm4py.objects.process_tree.obj import Operator
    # sequence operator
    SEQUENCE = Operator.SEQUENCE
    # exclusive choice operator
    XOR = Operator.XOR
    # parallel operator
    PARALLEL = Operator.PARALLEL
    # loop operator
    LOOP = Operator.LOOP
    # or operator
    OR = Operator.OR
    # interleaving operator
    INTERLEAVING = Operator.INTERLEAVING

    RECEIVE_MESSAGE = "receive_message"

    SEND_MESSAGE = "send_message"
    
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


# pm4py.objects.process_tree.obj.Operator = MyOperator
