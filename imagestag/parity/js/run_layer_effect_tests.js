#!/usr/bin/env node
/**
 * Run JavaScript parity tests for ImageStag layer effects.
 *
 * Usage:
 *   node imagestag/parity/js/run_layer_effect_tests.js
 *
 * Generates outputs to tmp/parity/layer_effects/ with naming:
 *   {effect}_{input}_js_u8.png
 *   {effect}_{input}_js_f32.png
 */

import { ParityTestRunner, config } from './runner.js';
import { initWasm, LAYER_EFFECT_CATALOG, registerAllEffects, getCatalogSummary } from './layer_effect_catalog.js';

async function main() {
    console.log('ImageStag Layer Effect Parity Tests (JavaScript)');
    console.log('=' .repeat(60));

    // Initialize WASM
    console.log('Initializing WASM...');
    await initWasm();
    console.log('WASM initialized.');
    console.log('');

    console.log(`Test directory: ${config.testDir}`);
    console.log(`Layer effect catalog: ${LAYER_EFFECT_CATALOG.length} effects`);
    console.log('');

    const runner = new ParityTestRunner();

    // Register all layer effects from the centralized catalog
    const registrationResults = registerAllEffects(runner);

    const registered = Object.values(registrationResults).filter(v => v).length;
    const failed = Object.entries(registrationResults)
        .filter(([_, v]) => !v)
        .map(([k, _]) => k);

    console.log(`Registered: ${registered} effects (u8 + f32 variants)`);
    if (failed.length > 0) {
        console.log(`Failed to register: ${failed.join(', ')}`);
    }
    console.log('');

    // Run tests
    console.log('Running all layer effect tests...');
    const results = await runner.runAllTests();

    // Print results
    console.log('\n' + '=' .repeat(60));
    console.log('Results:');
    console.log('=' .repeat(60));

    let totalPassed = 0;
    let totalFailed = 0;

    if (Object.keys(results.layer_effects).length > 0) {
        console.log('\n## LAYER_EFFECTS');

        for (const [name, testResults] of Object.entries(results.layer_effects)) {
            console.log(`\n### ${name}`);

            for (const result of testResults) {
                if (result.success) {
                    console.log(`  + ${result.id}: ${result.path}`);
                    totalPassed++;
                } else {
                    console.log(`  X ${result.id}: ${result.error}`);
                    totalFailed++;
                }
            }
        }
    }

    console.log('\n' + '=' .repeat(60));
    console.log(`Total: ${totalPassed} passed, ${totalFailed} failed`);
    console.log('=' .repeat(60));

    if (totalFailed > 0) {
        process.exit(1);
    }
}

main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
