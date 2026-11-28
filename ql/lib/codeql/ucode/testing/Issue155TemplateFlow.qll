/** Test-only interpolation-to-template-argument flow foundation for ucode #155. */
import codeql.ucode.DataFlow
import codeql.ucode.dataflow.TaintTracking
import codeql.ucode.ast.Calls
import codeql.ucode.ast.Expr
import codeql.ucode.ast.Misc
import codeql.ucode.ast.Variables
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.internal.SourceDeclaredFs
import codeql.ucode.Diagnostics
import codeql.ucode.m3.Models

private predicate rootIsVariable(UCODE::Expression expression, Variable variable) {
  exists(UCODE::Identifier root, VariableReadAccess read |
    expression = root and
    toTreeSitter(read.getAstNode()) = root and read.getVariable() = variable
  )
  or
  exists(UCODE::MemberExpression member |
    expression = member and rootIsVariable(member.getObject(), variable)
  )
  or
  exists(UCODE::SubscriptExpression subscript |
    expression = subscript and rootIsVariable(subscript.getObject(), variable)
  )
  or
  exists(UCODE::ParenthesizedExpression parenthesized |
    expression = parenthesized and rootIsVariable(parenthesized.getChild(), variable)
  )
}

/** The exact request property occurrence, rooted in a function formal. */
private predicate requestPropertySource(
  DataFlow::Node node, UCODE::Identifier formal, UCODE::FunctionExpression function
) {
  exists(
    UCODE::MemberExpression property, UCODE::MemberExpression args,
    UCODE::Identifier request, VariableReadAccess read, Variable variable
  |
    toTreeSitter(node.asExpr().getExpr()) = property and
    property.getProperty().getValue() = "service_name" and
    args = property.getObject() and args.getProperty().getValue() = "args" and
    request = args.getObject() and request.getValue() = "request" and
    toTreeSitter(read.getAstNode()) = request and
    variable = read.getVariable() and toTreeSitter(variable.getAstNode()) = formal and
    formal.getParent() = function.getParameters() and
    not exists(UCODE::Identifier duplicateFormal |
      duplicateFormal != formal and duplicateFormal.getValue() = "request" and
      duplicateFormal.getParent+() = function.getParameters()
    ) and
    property.getParent+() = function.getBody() and
    not exists(UCODE::FunctionExpression nested |
      nested != function and property.getParent+() = nested.getBody()
    ) and
    not exists(UCODE::FunctionDeclaration nested |
      property.getParent+() = nested.getBody()
    ) and
    not exists(UCODE::ArrowFunction nested |
      property.getParent+() = nested.getBody()
    ) and
    not exists(VariableWriteAccess write | write.getVariable() = variable) and
    not exists(UCODE::AssignmentExpression assignment |
      (exists(UCODE::MemberExpression write | assignment.getLeft() = write and rootIsVariable(write.getObject(), variable)) or
       exists(UCODE::SubscriptExpression write | assignment.getLeft() = write and rootIsVariable(write.getObject(), variable)))
    ) and
    not exists(UCODE::AugmentedAssignmentExpression assignment |
      (exists(UCODE::MemberExpression write | assignment.getLeft() = write and rootIsVariable(write.getObject(), variable)) or
       exists(UCODE::SubscriptExpression write | assignment.getLeft() = write and rootIsVariable(write.getObject(), variable)))
    ) and
    not exists(UCODE::UpdateExpression assignment |
      (exists(UCODE::MemberExpression write | assignment.getArgument() = write and rootIsVariable(write.getObject(), variable)) or
       exists(UCODE::SubscriptExpression write | assignment.getArgument() = write and rootIsVariable(write.getObject(), variable)))
    ) and
    not exists(UCODE::DeleteExpression deletion |
      deletion.getArgument() instanceof UCODE::Expression and
      rootIsVariable(deletion.getArgument().(UCODE::Expression), variable)
    ) and
    not exists(UCODE::VariableDeclarator declaration |
      declaration.getName().getValue() = "request" and
      declaration.getParent().getParent() = function.getBody()
    ) and
    not exists(UCODE::FunctionDeclaration declaration |
      declaration.getName().getValue() = "request" and
      declaration.getParent+() = function.getBody()
    ) and
    not exists(ExtractionError error | error.getLocation().getFile() = node.getLocation().getFile())
  )
}

/** An independently attributable fs.stat call with a template in argument 0. */
private predicate selectedStatTemplate(
  DataFlow::TemplateStringArgumentNode node, CallExpression call,
  UCODE::ImportSpecifier specifier, UCODE::FunctionExpression function
) {
  call.getTemplateArgument(0) = node.getTemplateString() and
  exists(SourceDeclaredFsStatCall statCall | statCall = toTreeSitter(call)) and
  toTreeSitter(call).getParent+() = function.getBody() and
  not exists(UCODE::FunctionExpression nested |
    nested != function and toTreeSitter(call).getParent+() = nested.getBody()
  ) and
  not exists(UCODE::FunctionDeclaration nested |
    toTreeSitter(call).getParent+() = nested.getBody()
  ) and
  not exists(UCODE::ArrowFunction nested |
    toTreeSitter(call).getParent+() = nested.getBody()
  ) and
  exists(UCODE::ImportStatement imp |
    specifier = imp.getClause().getNamed().getChild(_) and
    specifier.getName().(UCODE::Identifier).getValue() = "stat" and not exists(specifier.getAlias()) and
    imp.getSource().getChild(0).(UCODE::StringFragment).getValue() = "fs" and
    not exists(imp.getSource().getChild(1)) and
    imp.getLocation().getFile() = toTreeSitter(call).getLocation().getFile() and
    imp.getParent() instanceof UCODE::Program
  )
}

/** The test-only taint edge from one interpolation expression to its argument. */
predicate issue155InterpolationEdge(
  DataFlow::Node nodeFrom, DataFlow::Node nodeTo, TemplateSubstitution substitution
) {
  exists(
    DataFlow::TemplateStringArgumentNode argument,
    DataFlow::Node expression,
    CallExpression call,
    UCODE::ImportSpecifier specifier,
    UCODE::FunctionExpression function,
    int index
  |
    nodeTo = argument and
    selectedStatTemplate(argument, call, specifier, function) and
    call.getTemplateArgument(index) = argument.getTemplateString() and
    substitution.getParent() = argument.getTemplateString() and
    toTreeSitter(expression.asExpr().getExpr()) =
      substitution.getExpression().getRawAstNode() and
    nodeFrom = expression
  )
}

module WithInterpolationEdge implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
    exists(UCODE::Identifier formal, UCODE::FunctionExpression function |
      requestPropertySource(source, formal, function)
    )
  }

  predicate isSink(DataFlow::Node sink) {
    exists(CallExpression call, UCODE::ImportSpecifier specifier,
      UCODE::FunctionExpression function, UCODE::Identifier formal, DataFlow::Node source |
      selectedStatTemplate(sink.(DataFlow::TemplateStringArgumentNode), call, specifier, function) and
      requestPropertySource(source, formal, function)
    )
  }

  predicate isAdditionalFlowStep(DataFlow::Node nodeFrom, DataFlow::Node nodeTo) {
    exists(TemplateSubstitution substitution |
      issue155InterpolationEdge(nodeFrom, nodeTo, substitution)
    )
  }
}

module WithoutInterpolationEdge implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
    exists(UCODE::Identifier formal, UCODE::FunctionExpression function |
      requestPropertySource(source, formal, function)
    )
  }

  predicate isSink(DataFlow::Node sink) {
    exists(CallExpression call, UCODE::ImportSpecifier specifier,
      UCODE::FunctionExpression function, UCODE::Identifier formal, DataFlow::Node source |
      selectedStatTemplate(sink.(DataFlow::TemplateStringArgumentNode), call, specifier, function) and
      requestPropertySource(source, formal, function)
    )
  }
}

module FlowWithInterpolationEdge = TaintTracking::Global<WithInterpolationEdge>;
module FlowWithoutInterpolationEdge = TaintTracking::Global<WithoutInterpolationEdge>;

/** Exposes exact source, template-argument and call identities for test output. */
predicate issue155TemplateFlowWitness(
  DataFlow::Node source,
  DataFlow::TemplateStringArgumentNode argument, CallExpression call,
  UCODE::Identifier formal, UCODE::ImportSpecifier specifier,
  DataFlow::Node edgeSource, TemplateSubstitution substitution
) {
  exists(UCODE::FunctionExpression function |
    selectedStatTemplate(argument, call, specifier, function) and
    requestPropertySource(source, formal, function) and
    TaintTracking::localTaint(source, edgeSource) and
    issue155InterpolationEdge(edgeSource, argument, substitution)
  )
}

predicate issue155TemplateFlowRow(
  boolean withEdge, DataFlow::Node source,
  DataFlow::TemplateStringArgumentNode argument, CallExpression call,
  UCODE::Identifier formal, UCODE::ImportSpecifier specifier,
  DataFlow::Node edgeSource, TemplateSubstitution substitution
) {
  issue155TemplateFlowWitness(source, argument, call, formal, specifier, edgeSource, substitution) and
  (
    withEdge = true and FlowWithInterpolationEdge::flow(source, argument) or
    withEdge = false and FlowWithoutInterpolationEdge::flow(source, argument)
  )
}
