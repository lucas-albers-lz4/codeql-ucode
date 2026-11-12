import ucode
import codeql.ucode.controlflow.ControlFlowGraph
import TestUtils

class MyRelevantNode extends CfgNode {
  MyRelevantNode() { toBeTested(this.getScope()) }
}

import codeql.ucode.controlflow.internal.ControlFlowGraphImpl::TestOutput<MyRelevantNode>
