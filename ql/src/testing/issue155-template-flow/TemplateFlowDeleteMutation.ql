/** @name Issue 155 typed delete-argument mutation witnesses
 * @description Confirms delete controls use parenthesized and subscript AST arguments missed by a member-only guard.
 * @kind table
 * @id ucode/testing/issue155-template-flow-delete-mutation
 * @tags testing
 */
import codeql.ucode.ast.Misc
import codeql.ucode.ast.internal.TreeSitter

from UCODE::DeleteExpression deletion, UCODE::AstNode argument
where
  argument = deletion.getArgument() and
  (argument instanceof UCODE::ParenthesizedExpression or
    argument instanceof UCODE::SubscriptExpression) and
  deletion.getLocation().getFile().getRelativePath() in
    ["controls/delete-parenthesized.uc", "controls/delete-subscript.uc"]
select deletion.getLocation().getFile().getRelativePath() as path,
  argument as typed_delete_argument
