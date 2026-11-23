import codeql.ucode.m3.Models
import codeql.ucode.AST
private import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.TreeSitter

from Call call, NamedFsPopenCall sink, string method, TemplateString template, TemplateSubstitution sub,
 TemplateSubstitutionExpression input, DataFlow::ExprNode source, DataFlow::ExprNode substitution,
 UCODE::CallExpression sourceCall
where method = rpcMethodName(sink) and toTreeSitter(call) = sink and template = call.getTemplateArgument(0) and
 sub.getParent() = template and input = sub.getExpression() and
 toTreeSitter(substitution.getExprNode().getAstNode()) = input.getRawAstNode() and
 toTreeSitter(source.getExprNode().getAstNode()) = sourceCall and
 (method in ["getSwconfigFeatures", "getSwconfigPortState"] and sourceCall.getFunction().(UCODE::Identifier).getValue() = "shellquote" or
  sink.getLocation().getFile().getBaseName() = "controls.uc" and sourceCall.getFunction().(UCODE::Identifier).getValue() = "source") and
 DataFlow::localFlow(source, substitution)
select source, substitution, template, sink, method
