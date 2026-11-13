/**
 * @name storeStep / readStep from extracted member, subscript, object AST
 * @description Reports Field and Element store and read steps that match
 *              member properties, subscripts, object pairs, or array
 *              children. Testing only. Not production taint, not
 *              localFlowStep, and not setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/store-read
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.DataFlow
private import codeql.ucode.dataflow.internal.DataFlowPrivate

private string contentLabel(DataFlow::ContentSet c) {
  exists(DataFlow::FieldContent fc |
    c.isSingleton(fc) and
    result = "Field[" + fc.getName() + "]"
  )
  or
  exists(DataFlow::ElementContent ec |
    c.isSingleton(ec) and
    result = "Element"
  )
}

from File f, DataFlow::Node n1, DataFlow::Node n2, DataFlow::ContentSet c, string label
where
  (f.getBaseName() = "luci" or f.getBaseName() = "ssa_neg") and
  (
    storeStep(n1, c, n2) and
    n2.getLocation().getFile() = f and
    label = "store " + contentLabel(c)
    or
    readStep(n1, c, n2) and
    n2.getLocation().getFile() = f and
    label = "read " + contentLabel(c)
  )
select n2, label + " in " + f.getBaseName()
