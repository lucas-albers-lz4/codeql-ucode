import codeql.ucode.m3.Models
from RequestArgsAccess src, NamedFsPopenCall sink, string method
where src.getProperty().getValue() = "cmd" and method = rpcMethodName(sink) and sameRpcMethod(src, sink)
select src, method, sink
