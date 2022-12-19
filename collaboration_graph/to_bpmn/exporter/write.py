from pm4py.objects.bpmn.obj import BPMN


def write_bpmn(bpmn_graph: BPMN, file_path: str, enable_layout: bool = True):
    """
    Writes a BPMN to a file

    Parameters
    ---------------
    bpmn_graph
        BPMN
    file_path
        Destination path
    enable_layout
        Enables the automatic layouting of the BPMN diagram (default: True)
    """
    if enable_layout:
        from pm4py.objects.bpmn.layout import layouter
        bpmn_graph = layouter.apply(bpmn_graph)
    from collaboration_graph.to_bpmn import exporter
    exporter.apply(bpmn_graph, file_path)
