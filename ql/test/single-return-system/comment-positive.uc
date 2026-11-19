const methods = {
  setBlockDetect: { call: function() {
    // Plain comment, not an executable statement.
    return { result: system('/bin/true') == 0 };
  } }
};
return { luci: methods };
