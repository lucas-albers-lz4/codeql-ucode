const methods = {
  setBlockDetect: { call: function(system) {
    return { result: system('/bin/true') == 0 };
  } }
};
return { luci: methods };
