/**
 * @name SSA definition reads
 * @description SSA write-to-read pairs, including one phi join. Testing only; not a
 *              production taint query and not setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/ssa-reads
 * @tags testing
 */

import codeql.Locations
import codeql.files.FileSystem
import codeql.ucode.DataFlow
private import codeql.ucode.dataflow.internal.SsaImpl as SsaImpl

from Ssa::WriteDefinition def, Location readLoc
where
  readLoc = def.getARead().getLocation()
  or
  exists(SsaImpl::PhiDefinition phi |
    SsaImpl::Impl::phiHasInputFromBlock(phi, def, _) and
    readLoc = SsaImpl::getARead(phi).getLocation()
  )
select def,
  def.getSourceVariable().getName() + ":" + def.getLocation().getStartLine().toString() + " -> " +
    readLoc.getFile().getBaseName() + ":" + readLoc.getStartLine().toString()
