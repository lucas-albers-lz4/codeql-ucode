/** @name Testing-only raw template-flow ownership witnesses
 * @description Independently selects source, callable, import, call and substitution ASTs without the global flow helper.
 * @kind table
 * @id ucode/testing/issue155-template-flow-witnesses
 * @tags testing
 */
import codeql.ucode.DataFlow
import codeql.ucode.dataflow.TaintTracking
import codeql.ucode.ast.Calls
import codeql.ucode.ast.Expr
import codeql.ucode.ast.Misc
import codeql.ucode.ast.Variables
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.Diagnostics

private predicate rawRootIsVariable(UCODE::Expression expression, Variable variable) {
  exists(UCODE::Identifier root, VariableReadAccess read |
    expression = root and toTreeSitter(read.getAstNode()) = root and read.getVariable() = variable
  )
  or
  exists(UCODE::MemberExpression member |
    expression = member and rawRootIsVariable(member.getObject(), variable)
  )
  or
  exists(UCODE::SubscriptExpression subscript |
    expression = subscript and rawRootIsVariable(subscript.getObject(), variable)
  )
  or
  exists(UCODE::ParenthesizedExpression parenthesized |
    expression = parenthesized and rawRootIsVariable(parenthesized.getChild(), variable)
  )
}

private predicate rawFormalHasNoWrites(Variable variable) {
  not exists(VariableWriteAccess write | write.getVariable() = variable) and
  not exists(UCODE::AssignmentExpression assignment |
    exists(UCODE::MemberExpression member |
      assignment.getLeft() = member and rawRootIsVariable(member.getObject(), variable)
    ) or
    exists(UCODE::SubscriptExpression subscript |
      assignment.getLeft() = subscript and rawRootIsVariable(subscript.getObject(), variable)
    )
  ) and
  not exists(UCODE::AugmentedAssignmentExpression assignment |
    exists(UCODE::MemberExpression member |
      assignment.getLeft() = member and rawRootIsVariable(member.getObject(), variable)
    ) or
    exists(UCODE::SubscriptExpression subscript |
      assignment.getLeft() = subscript and rawRootIsVariable(subscript.getObject(), variable)
    )
  ) and
  not exists(UCODE::UpdateExpression assignment |
    exists(UCODE::MemberExpression member |
      assignment.getArgument() = member and rawRootIsVariable(member.getObject(), variable)
    ) or
    exists(UCODE::SubscriptExpression subscript |
      assignment.getArgument() = subscript and rawRootIsVariable(subscript.getObject(), variable)
    )
  )
  and not exists(UCODE::DeleteExpression deletion |
    deletion.getArgument() instanceof UCODE::Expression and
    rawRootIsVariable(deletion.getArgument().(UCODE::Expression), variable)
  )
}

from DataFlow::Node source, DataFlow::TemplateStringArgumentNode argument,
  CallExpression call, UCODE::Identifier formal, UCODE::ImportSpecifier specifier,
  DataFlow::Node edgeSource, TemplateSubstitution substitution,
  UCODE::FunctionExpression function, UCODE::MemberExpression sourceAst,
  UCODE::MemberExpression argsAst, UCODE::Identifier requestAst,
  VariableReadAccess sourceRead, Variable variable, UCODE::CallExpression rawCall
where
  toTreeSitter(source.asExpr().getExpr()) = sourceAst and
  sourceAst.getProperty().getValue() = "service_name" and
  argsAst = sourceAst.getObject() and argsAst.getProperty().getValue() = "args" and
  requestAst = argsAst.getObject() and requestAst.getValue() = "request" and
  toTreeSitter(sourceRead.getAstNode()) = requestAst and
  variable = sourceRead.getVariable() and toTreeSitter(variable.getAstNode()) = formal and
  formal.getParent() = function.getParameters() and
  not exists(UCODE::Identifier duplicateFormal |
    duplicateFormal != formal and duplicateFormal.getValue() = "request" and
    duplicateFormal.getParent+() = function.getParameters()
  ) and
  sourceAst.getParent+() = function.getBody() and
  not exists(UCODE::FunctionExpression nested |
    nested != function and sourceAst.getParent+() = nested.getBody()
  ) and
  not exists(UCODE::FunctionDeclaration nested | sourceAst.getParent+() = nested.getBody()) and
  not exists(UCODE::ArrowFunction nested | sourceAst.getParent+() = nested.getBody()) and
  rawFormalHasNoWrites(variable) and
  not exists(UCODE::VariableDeclarator declaration |
    declaration.getName().getValue() = "request" and
    declaration.getParent().getParent() = function.getBody()
  ) and
  not exists(UCODE::FunctionDeclaration declaration |
    declaration.getName().getValue() = "request" and declaration.getParent+() = function.getBody()
  ) and
  not exists(ExtractionError error | error.getLocation().getFile() = source.getLocation().getFile()) and
  rawCall = toTreeSitter(call) and
  rawCall.getFunction() instanceof UCODE::Identifier and
  rawCall.getFunction().(UCODE::Identifier).getValue() = "stat" and
  not exists(rawCall.getOptionalChain()) and
  call.getArgument(0) instanceof Expr and
  not exists(int i | i != 0 and exists(rawCall.getArguments().getChild(i))) and
  not exists(UCODE::SpreadElement spread | rawCall.getArguments().getChild(_) = spread) and
  call.getTemplateArgument(0) = argument.getTemplateString() and
  toTreeSitter(call).getParent+() = function.getBody() and
  not exists(UCODE::FunctionExpression nested |
    nested != function and toTreeSitter(call).getParent+() = nested.getBody()
  ) and
  not exists(UCODE::FunctionDeclaration nested | toTreeSitter(call).getParent+() = nested.getBody()) and
  not exists(UCODE::ArrowFunction nested | toTreeSitter(call).getParent+() = nested.getBody()) and
  exists(UCODE::ImportStatement imp |
    specifier = imp.getClause().getNamed().getChild(_) and
    specifier.getName().(UCODE::Identifier).getValue() = "stat" and
    not exists(specifier.getAlias()) and
    imp.getSource().getChild(0).(UCODE::StringFragment).getValue() = "fs" and
    not exists(imp.getSource().getChild(1)) and
    imp.getLocation().getFile() = rawCall.getLocation().getFile() and
    imp.getParent() instanceof UCODE::Program and
    (imp.getLocation().getEndLine() < rawCall.getLocation().getStartLine() or
      imp.getLocation().getEndLine() = rawCall.getLocation().getStartLine() and
      imp.getLocation().getEndColumn() < rawCall.getLocation().getStartColumn())
  ) and
  toTreeSitter(edgeSource.asExpr().getExpr()) = substitution.getExpression().getRawAstNode() and
  substitution.getParent() = argument.getTemplateString() and
  TaintTracking::localTaint(source, edgeSource)
select source.getLocation().getFile().getRelativePath() as path,
  source as source_node, argument as template_argument_node, call as call_node,
  formal as request_formal_node, specifier as stat_import_specifier_node,
  edgeSource as interpolation_edge_source_node, substitution as template_substitution_node,
  source.getLocation().getStartLine() as source_line,
  argument.getLocation().getStartLine() as template_line,
  call.getLocation().getStartLine() as call_line
