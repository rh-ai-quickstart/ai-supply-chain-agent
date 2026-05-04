/* eslint-env node */

import * as path from 'path';
import { Configuration as WebpackConfiguration, DefinePlugin } from 'webpack';
import { Configuration as WebpackDevServerConfiguration } from 'webpack-dev-server';
import { ConsoleRemotePlugin } from '@openshift-console/dynamic-plugin-sdk-webpack';

const CopyWebpackPlugin = require('copy-webpack-plugin');
// eslint-disable-next-line @typescript-eslint/no-require-imports -- build-time only
const pkg = require('./package.json') as { name: string; consolePlugin?: { name: string } };
const consolePluginName = pkg.consolePlugin?.name ?? pkg.name;

const isProd = process.env.NODE_ENV === 'production';
/** Empty = resolve API under the console plugin asset proxy (see apiClient). */
const supplyChainApiBaseUrl = process.env.SUPPLY_CHAIN_API_BASE_URL ?? '';

interface Configuration extends WebpackConfiguration {
  devServer?: WebpackDevServerConfiguration;
}

const config: Configuration = {
  mode: isProd ? 'production' : 'development',
  // No regular entry points needed. All plugin related scripts are generated via ConsoleRemotePlugin.
  entry: {},
  context: path.resolve(__dirname, 'src'),
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: isProd ? '[name]-bundle-[hash].min.js' : '[name]-bundle.js',
    chunkFilename: isProd ? '[name]-chunk-[chunkhash].min.js' : '[name]-chunk.js',
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx'],
  },
  module: {
    rules: [
      {
        test: /\.(jsx?|tsx?)$/,
        exclude: /\/node_modules\//,
        use: [
          {
            loader: 'ts-loader',
            options: {
              configFile: path.resolve(__dirname, 'tsconfig.json'),
            },
          },
        ],
      },
      {
        test: /\.(css)$/,
        use: ['style-loader', 'css-loader'],
      },
      {
        test: /\.(png|jpg|jpeg|gif|svg|woff2?|ttf|eot|otf)(\?.*$|$)/,
        type: 'asset/resource',
        generator: {
          filename: isProd ? 'assets/[contenthash][ext]' : 'assets/[name][ext]',
        },
      },
      {
        test: /\.(m?js)$/,
        resolve: {
          fullySpecified: false,
        },
      },
    ],
  },
  devServer: {
    static: './dist',
    port: 9001,
    // Allow Bridge running in a container to connect to the plugin dev server.
    allowedHosts: 'all',
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'X-Requested-With, Content-Type, Authorization',
    },
    devMiddleware: {
      writeToDisk: true,
    },
    // Same-origin /api/... during `yarn start` (empty build-time API base). Override target if needed.
    proxy: [
      {
        context: ['/api'],
        target: process.env.SUPPLY_CHAIN_DEV_API_PROXY_TARGET ?? 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
    ],
  },
  plugins: [
    new DefinePlugin({
      // Injected at build time so the browser bundle never references Node's `process`.
      'process.env.SUPPLY_CHAIN_API_BASE_URL': JSON.stringify(supplyChainApiBaseUrl),
      // Matches ConsoleRemotePlugin `publicPath` (`/api/plugins/<name>/`); console proxies this to the plugin pod.
      __SUPPLY_CHAIN_PLUGIN_HTTP_BASE__: JSON.stringify(`/api/plugins/${consolePluginName}/`),
    }),
    new ConsoleRemotePlugin(),
    new CopyWebpackPlugin({
      patterns: [{ from: path.resolve(__dirname, 'locales'), to: 'locales' }],
    }),
  ],
  devtool: isProd ? false : 'source-map',
  optimization: {
    chunkIds: isProd ? 'deterministic' : 'named',
    minimize: isProd,
  },
};

export default config;
