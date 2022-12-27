from pm4py.objects.bpmn.obj import BPMN


class EventBasedGateway(BPMN.Gateway):
    def __init__(self, id="", name="", gateway_direction=BPMN.Gateway.Direction.UNSPECIFIED, in_arcs=None,
                 out_arcs=None, process=None):
        BPMN.Gateway.__init__(self, id=id, name=name, gateway_direction=gateway_direction, in_arcs=in_arcs,
                              out_arcs=out_arcs, process=process)


class ReceiveMessageActivity(BPMN.Task):
    def __init__(self, id="", name="", in_arcs=None, out_arcs=None, process=None):
        BPMN.Task.__init__(self, id=id, name=name, in_arcs=in_arcs, out_arcs=out_arcs, process=process)


class SendMessageActivity(BPMN.Task):
    def __init__(self, id="", name="", in_arcs=None, out_arcs=None, process=None):
        BPMN.Task.__init__(self, id=id, name=name, in_arcs=in_arcs, out_arcs=out_arcs, process=process)
