import codeql.ucode.MarkupCFG
import codeql.ucode.MarkupCreationCFG

string status(UcodeMarkup::Markup root) {
  MarkupCFG::isCovered(root) and result = "foundation-covered"
  or
  MarkupCreationCFG::hasTopLevelObservation(root) and result = "top-observed"
}

from UcodeMarkup::Markup root
select root.getLocation().getFile().getBaseName(), status(root)
