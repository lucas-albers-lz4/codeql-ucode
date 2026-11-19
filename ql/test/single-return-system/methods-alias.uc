const methods = {
  setBlockDetect: { call: function() {
    return { result: system('/bin/true') == 0 };
  } }
};
let alias = methods;
return { luci: methods };
