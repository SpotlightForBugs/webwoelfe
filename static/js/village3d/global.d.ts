/**
 * Global type declarations for PlayCanvas runtime
 * PlayCanvas is loaded at runtime via <script> tag and exposes itself on window.pc
 */

import * as pc from "playcanvas";

declare global {
  interface Window {
    pc: typeof pc;
  }
}

export {};
