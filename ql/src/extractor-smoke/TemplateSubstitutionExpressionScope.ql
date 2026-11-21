/**
 * @name Template substitution expression wrapper scope
 * @description Reports expression wrappers that are not direct children of a
 *              TemplateSubstitution. An empty result is required.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-substitution-expression-scope
 * @tags testing
 */

import codeql.ucode.AST
private import codeql.ucode.ast.internal.TreeSitter

from TemplateSubstitutionExpression expression
where
  not exists(UCODE::TemplateSubstitution substitution |
    expression.getRawAstNode() = substitution.getChild()
  )
select expression,
  "expression wrapper is not a template substitution child: " + expression.getExpressionKind()
