/** @name Testing-only DDNS stat source observation
 * @description Testing-only source attribution and lexical request binding; no flow or sink claim.
 * @kind table
 * @tags testing
 * @id ucode/inventory/issue-155-stat-observation
 */
import codeql.files.FileSystem
import codeql.ucode.ast.Variables
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.Diagnostics

/** A local identifier introduced by any import clause in `imp`. */
private UCODE::Identifier statImportBinding(UCODE::ImportStatement imp) {
  exists(UCODE::ImportSpecifier spec |
    spec = imp.getClause().getNamed().getChild(_) and
    (result = spec.getAlias() or not exists(spec.getAlias()) and result = spec.getName())
  )
  or result = imp.getClause().getDefault()
  or result = imp.getClause().getNamespace().getChild()
}

/** Competing binding or write, checked across the entire file. */
private predicate statCompetingBindingOrWrite(UCODE::Identifier id) {
  exists(UCODE::VariableDeclarator d | d.getName() = id)
  or exists(UCODE::FunctionDeclaration f | f.getName() = id)
  or exists(UCODE::FunctionExpression f | f.getName() = id)
  or exists(UCODE::FormalParameters ps | id = ps.getChild(_))
  or exists(UCODE::RestElement rest, UCODE::FormalParameters ps |
    rest = ps.getChild(_) and id = rest.getChild()
  )
  or exists(UCODE::ArrowFunction f | f.getParameter() = id)
  or exists(UCODE::CatchClause c | c.getParameter() = id)
  or exists(UCODE::ForInStatement f | id = f.getVariable() or id = f.getKey() or id = f.getValue())
  or exists(UCODE::ForInAltStatement f | id = f.getVariable() or id = f.getKey() or id = f.getValue())
  or exists(UCODE::AssignmentExpression a | a.getLeft() = id)
  or exists(UCODE::AugmentedAssignmentExpression a | a.getLeft() = id)
  or exists(UCODE::UpdateExpression u | u.getArgument() = id)
}


private predicate key(UCODE::AstNode n, string name) {
  n.(UCODE::PropertyIdentifier).getValue() = name
}
private predicate sourceDeclaredStat(UCODE::CallExpression call, UCODE::Identifier callee,
    UCODE::ImportStatement imp, UCODE::ImportSpecifier spec) {
  callee = call.getFunction() and callee.getValue() = "stat" and
  not exists(call.getOptionalChain()) and
  imp.getLocation().getFile() = call.getLocation().getFile() and imp.getParent() instanceof UCODE::Program and
  (imp.getLocation().getEndLine() < call.getLocation().getStartLine() or
   imp.getLocation().getEndLine() = call.getLocation().getStartLine() and
   imp.getLocation().getEndColumn() < call.getLocation().getStartColumn()) and
  spec = imp.getClause().getNamed().getChild(_) and
  spec.getName().(UCODE::Identifier).getValue() = "stat" and not exists(spec.getAlias()) and
  imp.getSource().getChild(0).(UCODE::StringFragment).getValue() = "fs" and
  not exists(imp.getSource().getChild(1)) and
  strictcount(UCODE::ImportStatement other, UCODE::Identifier id |
    id = statImportBinding(other) and other.getLocation().getFile() = call.getLocation().getFile() and
    id.getValue() = "stat") = 1 and
  not exists(UCODE::Identifier id | id.getLocation().getFile() = call.getLocation().getFile() and
    id.getValue() = "stat" and statCompetingBindingOrWrite(id)) and
  not exists(ExtractionError error | error.getLocation().getFile() = call.getLocation().getFile())
}

private predicate selectedHandler(UCODE::CallExpression call, UCODE::FunctionExpression handler) {
  exists(UCODE::Pair method, UCODE::Pair callField, UCODE::Object methodBody,
         UCODE::Object methods, UCODE::VariableDeclarator declaration,
         UCODE::Pair rpc, UCODE::Object returned, UCODE::ReturnStatement ret,
         UCODE::Identifier methodsRead, VariableReadAccess read, string rpcName, string methodName |
    (call.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/ddns.uc" and
     rpcName = "luci.ddns" and methodName = "get_services_log" or
     call.getLocation().getFile().getRelativePath() = ["controls/positive-direct.uc", "controls/positive-post-call-property.uc", "controls/negative-shadow.uc", "controls/negative-reassignment.uc", "controls/negative-other-module.uc", "controls/negative-fixed-path.uc", "controls/negative-readfile.uc", "controls/negative-optional-call.uc", "controls/negative-aliased-import.uc", "controls/negative-request-shadow.uc", "controls/negative-duplicate.uc"] and
     rpcName = "luci.review.stat" and methodName = "observe") and
    call.getParent*() = handler.getBody() and
    not exists(UCODE::AstNode nested | nested = call.getParent+() and
      nested.getParent*() = handler.getBody() and
      (nested instanceof UCODE::FunctionExpression or nested instanceof UCODE::FunctionDeclaration or
       nested instanceof UCODE::ArrowFunction)) and
    callField.getValue() = handler and key(callField.getKey(), "call") and
    callField = methodBody.getChild(_) and method.getValue() = methodBody and key(method.getKey(), methodName) and
    method = methods.getChild(_) and declaration.getValue() = methods and declaration.getName().getValue() = "methods" and
    rpc.getValue() = methodsRead and methodsRead.getValue() = "methods" and
    rpc.getKey().(UCODE::String).getChild(0).(UCODE::StringFragment).getValue() = rpcName and
    not exists(rpc.getKey().(UCODE::String).getChild(1)) and rpc = returned.getChild(_) and
    ret.getChild() = returned and ret.getParent() instanceof UCODE::Program and
    read.getAstNode() = TIdentifier(methodsRead) and toTreeSitter(read.getVariable().getAstNode()) = declaration and
    strictcount(Variable target | exists(VariableReadAccess a | a.getAstNode() = TIdentifier(methodsRead) and a.getVariable() = target)) = 1
  )
}

from UCODE::CallExpression call, UCODE::Identifier callee, UCODE::ImportStatement imp,
  UCODE::ImportSpecifier spec, UCODE::FunctionExpression handler, UCODE::Identifier formal,
  UCODE::TemplateString arg, UCODE::TemplateSubstitution sub, UCODE::MemberExpression property,
  UCODE::MemberExpression args, UCODE::Identifier receiver, VariableReadAccess read
where
  sourceDeclaredStat(call, callee, imp, spec) and selectedHandler(call, handler) and
  formal = handler.getParameters().getChild(0) and formal.getValue() = "request" and
  not exists(handler.getParameters().getChild(1)) and
  arg = call.getArguments().getChild(0) and not exists(call.getArguments().getChild(1)) and
  sub = arg.getChild(_) and property = sub.getChild() and
  property.getProperty().getValue() = "service_name" and not exists(property.getOptionalChain()) and
  args = property.getObject() and args.getProperty().getValue() = "args" and not exists(args.getOptionalChain()) and
  receiver = args.getObject() and receiver.getValue() = "request" and
  read.getAstNode() = TIdentifier(receiver) and read.getVariable().getAstNode() = TIdentifier(formal) and
  strictcount(Variable target | exists(VariableReadAccess a | a.getAstNode() = TIdentifier(receiver) and a.getVariable() = target)) = 1
select call.getLocation().getFile().getRelativePath() as path, call as call_node, callee as callee_node,
  imp as import_node, spec as specifier_node, handler as handler_node, formal as formal_node,
  arg as argument_node, sub as substitution_node, property as property_node,
  args as args_node, receiver as receiver_node
