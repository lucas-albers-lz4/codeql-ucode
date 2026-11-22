import codeql.ucode.MarkupCFG
import codeql.ucode.MarkupCreationCFG

from UcodeMarkup::Markup root, string ordinary, string creation
where
  (MarkupCFG::isCovered(root) and ordinary = "covered" or not MarkupCFG::isCovered(root) and ordinary = "unsupported") and
  (MarkupCreationCFG::hasTopLevelObservation(root) and creation = "covered" or not MarkupCreationCFG::hasTopLevelObservation(root) and creation = "unsupported")
select root.getLocation().getFile().getRelativePath(), ordinary, creation,
  count(UcodeMarkup::AstNode n | n.getParent+() = root)
