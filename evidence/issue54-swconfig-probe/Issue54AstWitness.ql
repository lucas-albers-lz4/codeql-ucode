import codeql.ucode.m3.Models
from RequestArgsAccess src, NamedCall helper, NamedFsPopenCall sink, string method
where method = rpcMethodName(sink) and method in ["getSwconfigFeatures", "getSwconfigPortState"] and
  src.getProperty().getValue() = "switch" and helper.getName() = "shellquote" and
  src = helper.getArgument(0) and helper.getParent*() = sink.getArgument(0)
select src, helper, sink, method
