/**
 * @name Template literal fragment rows
 * @description Exact direct string-fragment identities in selected templates.
 *              Testing only; fragment text is not a value-flow node.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-literal-part-rows
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST

private predicate isTargetTemplate(TemplateString template) {
  template.getFile().getRelativePath() = "template_args.uc"
  or
  template.getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
  template.getLocation().getStartLine() in [343, 474]
}

from TemplateString template, StringFragment fragment
where
  isTargetTemplate(template) and
  fragment = template.getAChild()
select fragment,
  "literal fragment at " + fragment.getLocation().getStartLine().toString() + ":" +
    fragment.getLocation().getStartColumn().toString() + "-" +
    fragment.getLocation().getEndLine().toString() + ":" +
    fragment.getLocation().getEndColumn().toString() + " in " + template.getFile().getRelativePath()
