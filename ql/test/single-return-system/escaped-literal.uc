const methods = {
  setBlockDetect: { call: function() {
    return { result: system('/bin/tr\x75e') == 0 };
  } }
};
return { luci: methods };
