import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'index',
    {
      type: 'category',
      label: 'Get Started',
      link: {
        type: 'doc',
        id: 'get-started/index',
      },
      items: [
        'get-started/install',
        'get-started/quickstart',
      ],
    },
    {
      type: 'category',
      label: 'Quickstarts',
      link: {
        type: 'doc',
        id: 'quickstarts/index',
      },
      items: [
        'quickstarts/openai',
        'quickstarts/openai_agents',
        'quickstarts/openrouter',
        'quickstarts/litellm',
        'quickstarts/gemini',
        'quickstarts/fireworks',
        'quickstarts/together',
        'quickstarts/langchain',
        'quickstarts/langgraph',
      ],
    },
    {
      type: 'category',
      label: 'Concepts',
      link: {
        type: 'doc',
        id: 'concepts/index',
      },
      items: [
        'concepts/acting_on_decisions',
        'concepts/reading_results',
        'concepts/policies',
        'concepts/tolerance',
        'concepts/segmentation',
        'concepts/provider_capabilities',
        'concepts/canonical_vs_realized',
        'concepts/capability_tiers',
        'concepts/research_grounding',
        'concepts/testing',
        'concepts/troubleshooting',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      link: {
        type: 'doc',
        id: 'concepts/public_api',
      },
      items: [
        'reference/root-api',
        'reference/config-models',
        'reference/results-and-records',
        'reference/adapters',
        'reference/integrations',
        'reference/utilities-and-errors',
      ],
    },
    {
      type: 'category',
      label: 'Maintainers',
      link: {
        type: 'doc',
        id: 'maintainers/index',
      },
      items: [
        'maintainers/versioning',
        'maintainers/integration_source_review',
      ],
    },
  ],
};

export default sidebars;
