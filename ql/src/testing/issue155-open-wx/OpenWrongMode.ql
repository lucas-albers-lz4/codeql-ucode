/** @name Testing-only open wrong-mode-slot counterfactual
 * @description Selects wx at slot zero instead of slot one, for source-first discrimination.
 * @kind table
 * @id ucode/testing/issue155-open-wx-wrong-mode
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs
from UCODE::CallExpression call, UCODE::String pathArg, UCODE::AstNode mode
where sourceDeclaredFsCall(call, "open") and pathArg = call.getArguments().getChild(0) and
  pathArg.getChild(0).(UCODE::StringFragment).getValue() = "wx" and not exists(pathArg.getChild(1)) and
  mode = call.getArguments().getChild(1) and mode instanceof UCODE::Expression and
  (not exists(call.getArguments().getChild(2)) or call.getArguments().getChild(2) instanceof UCODE::Expression) and
  not exists(int i | i != 0 and i != 1 and i != 2 and exists(call.getArguments().getChild(i)))
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  call.getFunction() as callee_node, pathArg as path_node, mode as mode_node
