import codeql.ucode.MarkupCFG

from UcodeMarkup::Markup root, string covered
where
  root.getLocation().getFile().getBaseName() =
    ["plain.ut", "trim-open.ut", "trim-close.ut", "trim-both.ut", "ordinary-member.ut", "trim-member.ut"] and
  (if MarkupCFG::isCovered(root) then covered = "covered" else covered = "unsupported")
select root.getLocation().getFile().getBaseName(), covered
