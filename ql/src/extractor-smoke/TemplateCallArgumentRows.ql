/**
 * @name Direct template-string call argument rows
 * @description Exact direct template argument identities, child parts, and
 *              substitutions. Testing only; no template value-flow model.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-call-argument-rows
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

from Call call, int argumentIndex, TemplateString template, File file
where
  template = call.getTemplateArgument(argumentIndex) and
  isTargetTemplate(template) and
  file = template.getFile() and
  (
    file.getRelativePath() = "usr/share/rpcd/ucode/luci" or
    file.getRelativePath() = "template_args.uc"
  )
select template,
  call.getIdentifier().getName() + " template arg " + argumentIndex.toString() + " at " +
    template.getLocation().getStartLine().toString() + ":" +
    template.getLocation().getStartColumn().toString() + "-" +
    template.getLocation().getEndLine().toString() + ":" +
    template.getLocation().getEndColumn().toString() + " in " + file.getRelativePath()
