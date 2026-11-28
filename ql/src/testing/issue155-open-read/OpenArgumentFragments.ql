/** @name Testing-only open call argument literal fragments
 * @description Raw argument string values and indexes without classifying a call.
 * @kind table
 * @id ucode/testing/issue155-open-read-argument-fragments
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
from UCODE::CallExpression call, UCODE::String argString, UCODE::StringFragment frag, int i
where
  (call.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci.upnp" or
   call.getLocation().getFile().getRelativePath().matches("controls/%")) and
  call.getFunction().(UCODE::Identifier).getValue() = "open" and
  argString = call.getArguments().getChild(i) and frag = argString.getChild(_)
select call.getLocation().getFile().getRelativePath() as path, call as call_node, i as argument_index,
  argString as string_node, frag as fragment_node, frag.getValue() as value
