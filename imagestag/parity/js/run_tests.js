#!/usr/bin/env node
/**
 * Run JavaScript parity tests for ImageStag filters and effects.
 *
 * Usage:
 *   node imagestag/parity/js/run_tests.js
 *   node imagestag/parity/js/run_tests.js --filter grayscale
 *   node imagestag/parity/js/run_tests.js --category filters
 *
 * This script runs all registered JS parity tests and saves outputs to
 * the shared temp directory for comparison with Python.
 */

import { ParityTestRunner, config } from './runner.js';
import { registerAllFilters, FILTER_CATALOG, getCatalogSummary } from './filter_catalog.js';

// Parse command line arguments
const args = process.argv.slice(2);
let filterName = null;
let category = null;
let showCatalog = false;

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--filter' && args[i + 1]) {
        filterName = args[i + 1];
        i++;
    } else if (args[i] === '--category' && args[i + 1]) {
        category = args[i + 1];
        i++;
    } else if (args[i] === '--catalog') {
        showCatalog = true;
    }
}

async function main() {
    if (showCatalog) {
        console.log(getCatalogSummary());
        return;
    }

    console.log('ImageStag Cross-Platform Parity Tests (JavaScript)');
    console.log('=' .repeat(50));
    console.log(`Test directory: ${config.testDir}`);
    console.log(`Output format: ${config.outputFormat}`);
    console.log(`Filter catalog: ${FILTER_CATALOG.length} base filters`);
    console.log('');

    const runner = new ParityTestRunner();

    // Register all filters from the centralized catalog
    const registrationResults = registerAllFilters(runner);

    const registered = Object.values(registrationResults).filter(v => v).length;
    const failed = Object.entries(registrationResults)
        .filter(([_, v]) => !v)
        .map(([k, _]) => k);

    console.log(`Registered: ${registered} filters (u8 + f32 variants)`);
    if (failed.length > 0) {
        console.log(`Failed to register: ${failed.join(', ')}`);
    }
    console.log('');

    // Run tests
    let results;
    if (filterName) {
        console.log(`Running tests for filter: ${filterName}`);
        try {
            const filterResults = await runner.runFilterTests(filterName);
            results = {
                filters: { [filterName]: filterResults },
                layer_effects: {}
            };
        } catch (err) {
            console.error(`Error: ${err.message}`);
            process.exit(1);
        }
    } else if (category === 'filters') {
        console.log('Running all filter tests...');
        results = await runner.runAllTests();
        results.layer_effects = {};
    } else if (category === 'layer_effects') {
        console.log('Running all layer effect tests...');
        results = await runner.runAllTests();
        results.filters = {};
    } else {
        console.log('Running all tests...');
        results = await runner.runAllTests();
    }

    // Print results
    console.log('\n' + '=' .repeat(50));
    console.log('Results:');
    console.log('=' .repeat(50));

    let totalPassed = 0;
    let totalFailed = 0;

    for (const [cat, tests] of Object.entries(results)) {
        if (Object.keys(tests).length === 0) continue;

        console.log(`\n## ${cat.toUpperCase()}`);

        for (const [name, testResults] of Object.entries(tests)) {
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

    console.log('\n' + '=' .repeat(50));
    console.log(`Total: ${totalPassed} passed, ${totalFailed} failed`);
    console.log('=' .repeat(50));

    if (totalFailed > 0) {
        process.exit(1);
    }
}

main().catch(err => {
    console.error('Error running tests:', err);
    process.exit(1);
});
