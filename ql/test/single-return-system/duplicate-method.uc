const methods = {
  setBlockDetect: { call: function() { return { result: system('/bin/true') == 0 }; } },
  setBlockDetect: { call: function() { return { result: system('/bin/true') == 0 }; } }
};
return { luci: methods };
