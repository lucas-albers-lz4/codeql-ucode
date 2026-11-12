import codeql.ucode.dataflow.internal.TaintTrackingPublic as Public

module Private {
  import codeql.ucode.dataflow.DataFlow::DataFlow as DataFlow
  import codeql.ucode.dataflow.internal.DataFlowImpl as DataFlowInternal
  import codeql.ucode.dataflow.internal.TaintTrackingPrivate
}