import inspect
import unittest

import pipeline


class TestPipelineIntegration(unittest.TestCase):

    def test_pipeline_exports_meet2reqs_functions(self):
        """Verify that pipeline.py exports the meet2reqs pipeline functions."""
        self.assertTrue(hasattr(pipeline, "process_transcript"), "pipeline.process_transcript missing")
        self.assertTrue(hasattr(pipeline, "extract_requirements"), "pipeline.extract_requirements missing")
        self.assertTrue(hasattr(pipeline, "extract_action_items"), "pipeline.extract_action_items missing")
        self.assertTrue(hasattr(pipeline, "extract_decisions"), "pipeline.extract_decisions missing")
        self.assertTrue(hasattr(pipeline, "extract_emphasis_points"), "pipeline.extract_emphasis_points missing")
        self.assertTrue(hasattr(pipeline, "enrich_requirements"), "pipeline.enrich_requirements missing")
        self.assertTrue(hasattr(pipeline, "validate_extraction"), "pipeline.validate_extraction missing")
        self.assertTrue(hasattr(pipeline, "generate_pdf"), "pipeline.generate_pdf missing")

        # Verify they are callable
        self.assertTrue(callable(pipeline.process_transcript))
        self.assertTrue(callable(pipeline.extract_requirements))
        self.assertTrue(callable(pipeline.generate_pdf))

    def test_pipeline_exports_formatting_functions(self):
        """Verify that pipeline.py still exports formatting pipeline functions."""
        self.assertTrue(hasattr(pipeline, "format_transcript"), "pipeline.format_transcript missing")
        self.assertTrue(hasattr(pipeline, "validate_format"), "pipeline.validate_format missing")
        self.assertTrue(hasattr(pipeline, "add_yaml"), "pipeline.add_yaml missing")
        self.assertTrue(hasattr(pipeline, "validate_headers"), "pipeline.validate_headers missing")

    def test_pipeline_exports_legacy_functions(self):
        """Verify backward compatibility with legacy pipeline functions."""
        self.assertTrue(hasattr(pipeline, "summarize_transcript"), "pipeline.summarize_transcript missing")
        self.assertTrue(hasattr(pipeline, "generate_structured_summary"), "pipeline.generate_structured_summary missing")

if __name__ == '__main__':
    unittest.main()
