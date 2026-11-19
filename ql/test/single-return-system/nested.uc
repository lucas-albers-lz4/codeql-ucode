const methods = {
  setBlockDetect: { call: function() {
    function nested() { return { result: system('/bin/true') == 0 }; }
    return nested();
  } }
};
return { luci: methods };
