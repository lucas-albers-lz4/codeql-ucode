const methods = {
  setBlockDetect: { call: function() {
    return { result: runner.system('/bin/true') == 0 };
  } }
};
return { luci: methods };
