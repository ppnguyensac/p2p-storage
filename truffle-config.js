module.exports = {
  networks: {
    development: {
      host: "127.0.0.1",   // Ganache CLI RPC host
      port: 8545,          // Ganache CLI default port
      network_id: "*"      // Match any network id
    }
  },

  // Set default mocha options
  mocha: {
    timeout: 100000
  },

  // Configure your compilers
  compilers: {
    solc: {
      version: "0.8.20",   // or any Solidity 0.8.x version you're using
      settings: {
        optimizer: {
          enabled: true,
          runs: 200
        }
      }
    }
  }
};

