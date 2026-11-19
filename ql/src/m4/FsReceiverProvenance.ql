/**
 * Source-declared popen receiver provenance only. No runtime call target,
 * path, flow, taint, or security conclusion is implied by these rows.
 */

import FsReceiverOrigin

from
  UCODE::CallExpression call, UCODE::VariableDeclarator decl, UCODE::CallExpression initializer,
  UCODE::Identifier receiver, string method, string factory
where
  receiverOrigin(call, decl, initializer, method, factory) and
  directMember(call, receiver, method)
select call, receiver, decl, initializer, method, factory
