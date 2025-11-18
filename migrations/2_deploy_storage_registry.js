const StorageRegistry = artifacts.require("StorageRegistry");

module.exports = function (deployer) {
  deployer.deploy(StorageRegistry);
};

