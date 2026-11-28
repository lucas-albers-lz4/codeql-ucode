/** @name Testing-only open import fragment witnesses
 * @description Import syntax and literal fragments, without runtime resolution.
 * @kind table
 * @id ucode/testing/issue155-open-read-import-fragments
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
from UCODE::ImportStatement imp, UCODE::ImportSpecifier spec, UCODE::StringFragment frag
where
  (imp.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci.upnp" or
   imp.getLocation().getFile().getRelativePath().matches("controls/%")) and
  spec = imp.getClause().getNamed().getChild(_) and
  (spec.getName().(UCODE::Identifier).getValue() = "open" or spec.getAlias().getValue() = "open") and
  frag = imp.getSource().getChild(_)
select imp.getLocation().getFile().getRelativePath() as path, imp as import_node,
  frag as fragment_node, frag.getValue() as value
