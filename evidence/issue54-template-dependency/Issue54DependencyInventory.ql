import codeql.ucode.m3.Models
import codeql.ucode.AST
private import codeql.ucode.ast.internal.AstNodes
from Call call, NamedFsPopenCall sink, string method, TemplateString template
where method = rpcMethodName(sink) and toTreeSitter(call) = sink and template = call.getTemplateArgument(0) and
 (method in ["getSwconfigFeatures", "getSwconfigPortState"] or sink.getLocation().getFile().getBaseName() = "controls.uc")
select sink, template, method
