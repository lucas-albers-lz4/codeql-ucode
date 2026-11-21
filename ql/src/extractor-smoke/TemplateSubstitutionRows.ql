/**
 * @name Direct template-string substitution rows
 * @description Exact substitution identity and order in direct templates.
 *              Testing only; no template value-flow model.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-substitution-rows
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST

private int substitutionPosition(TemplateString template, TemplateSubstitution sub) {
  sub.getParent() = template and
  result =
    count(TemplateSubstitution previous |
      previous.getParent() = template and
      (
        previous.getLocation().getStartLine() < sub.getLocation().getStartLine()
        or
        previous.getLocation().getStartLine() = sub.getLocation().getStartLine() and
        previous.getLocation().getStartColumn() < sub.getLocation().getStartColumn()
      )
    )
}

private predicate isTargetTemplate(TemplateString template) {
  template.getFile().getRelativePath() = "template_args.uc"
  or
  template.getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
  template.getLocation().getStartLine() in [343, 474]
}

from Call call, int argumentIndex, TemplateString template, TemplateSubstitution sub, File file
where
  template = call.getTemplateArgument(argumentIndex) and
  isTargetTemplate(template) and
  sub.getParent() = template and
  file = template.getFile() and
  (
    file.getRelativePath() = "usr/share/rpcd/ucode/luci" or
    file.getRelativePath() = "template_args.uc"
  )
select sub,
  call.getIdentifier().getName() + " arg " + argumentIndex.toString() + " template " +
    template.getLocation().getStartLine().toString() + ":" +
    template.getLocation().getStartColumn().toString() + "; substitution " +
    substitutionPosition(template, sub).toString() + " at " +
    sub.getLocation().getStartLine().toString() + ":" +
    sub.getLocation().getStartColumn().toString() + "-" + sub.getLocation().getEndLine().toString() +
    ":" + sub.getLocation().getEndColumn().toString() + " in " + file.getRelativePath()
