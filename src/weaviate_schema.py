"""
Weaviate schema management with versioning for ZenGlow RAG pipeline
"""
import weaviate
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WeaviateSchemaManager:
    """Manages Weaviate schema with versioning support"""
    
    def __init__(self, client: weaviate.Client):
        self.client = client
        
    def get_wellness_context_schema(self, version: str = "v1") -> Dict[str, Any]:
        """Get schema definition for WellnessContext class"""
        class_name = f"WellnessContext_{version}"
        
        schema = {
            "class": class_name,
            "description": f"Wellness context data for children - version {version}",
            "vectorizer": "none",  # We provide our own vectors
            "properties": [
                {
                    "name": "text",
                    "dataType": ["text"],
                    "description": "Rich text description of the wellness context"
                },
                {
                    "name": "child_id",
                    "dataType": ["string"],
                    "description": "Unique identifier for the child"
                },
                {
                    "name": "timestamp",
                    "dataType": ["number"],
                    "description": "Unix timestamp of the data point"
                },
                {
                    "name": "idempotency_key",
                    "dataType": ["string"],
                    "description": "Unique key to prevent duplicate entries"
                },
                {
                    "name": "version",
                    "dataType": ["string"],
                    "description": "Schema version"
                },
                {
                    "name": "wellness_metrics",
                    "dataType": ["object"],
                    "description": "Wellness metrics data",
                    "nestedProperties": [
                        {
                            "name": "hr",
                            "dataType": ["number"],
                            "description": "Heart rate in BPM"
                        },
                        {
                            "name": "stress",
                            "dataType": ["number"],
                            "description": "Stress level (0-1)"
                        },
                        {
                            "name": "sleep_duration",
                            "dataType": ["number"],
                            "description": "Sleep duration in seconds"
                        },
                        {
                            "name": "sleep_state",
                            "dataType": ["string"],
                            "description": "Sleep state (awake/light/deep/REM)"
                        }
                    ]
                },
                {
                    "name": "context",
                    "dataType": ["object"],
                    "description": "Additional context data",
                    "nestedProperties": [
                        {
                            "name": "school_events",
                            "dataType": ["string"],
                            "description": "School events description"
                        },
                        {
                            "name": "user_profile",
                            "dataType": ["object"],
                            "description": "User profile data",
                            "nestedProperties": [
                                {
                                    "name": "age",
                                    "dataType": ["int"],
                                    "description": "Child's age"
                                }
                            ]
                        }
                    ]
                },
                {
                    "name": "interaction",
                    "dataType": ["object"],
                    "description": "Interaction event data",
                    "nestedProperties": [
                        {
                            "name": "event",
                            "dataType": ["string"],
                            "description": "Interaction event description"
                        }
                    ]
                }
            ]
        }
        
        return schema
    
    def create_class_if_not_exists(self, version: str = "v1", expected_vector_dimension: int = 1024) -> bool:
        """
        Create WellnessContext class if it doesn't exist
        
        Args:
            version: Schema version
            expected_vector_dimension: Expected embedding vector dimension
            
        Returns:
            True if class was created or already exists, False if error
        """
        class_name = f"WellnessContext_{version}"
        
        try:
            # Check if class exists
            existing_schema = self.client.schema.get()
            existing_classes = [cls['class'] for cls in existing_schema.get('classes', [])]
            
            if class_name in existing_classes:
                logger.info(f"Class {class_name} already exists")
                
                # Verify vector dimension if possible
                if not self._verify_vector_dimension(class_name, expected_vector_dimension):
                    logger.warning(f"Vector dimension mismatch for {class_name}")
                    return False
                
                return True
            
            # Create new class
            schema = self.get_wellness_context_schema(version)
            self.client.schema.create_class(schema)
            
            logger.info(f"Created Weaviate class: {class_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create/verify class {class_name}: {e}")
            return False
    
    def _verify_vector_dimension(self, class_name: str, expected_dimension: int) -> bool:
        """
        Verify that existing vectors have the expected dimension
        This is a simplified check - in production you might want more sophisticated validation
        """
        try:
            # Get a sample object to check vector dimension
            result = self.client.query.get(class_name).with_additional(['vector']).with_limit(1).do()
            
            objects = result.get('data', {}).get('Get', {}).get(class_name, [])
            if not objects:
                # No objects exist yet, assume dimension is correct
                return True
            
            vector = objects[0].get('_additional', {}).get('vector')
            if vector and len(vector) != expected_dimension:
                logger.error(f"Vector dimension mismatch: expected {expected_dimension}, got {len(vector)}")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Could not verify vector dimension for {class_name}: {e}")
            # If we can't verify, assume it's OK rather than blocking
            return True
    
    def recreate_class_if_dimension_mismatch(self, version: str = "v1", 
                                           expected_dimension: int = 1024,
                                           force_recreate: bool = False) -> bool:
        """
        Recreate class if vector dimension doesn't match
        
        Args:
            version: Schema version
            expected_dimension: Expected vector dimension
            force_recreate: If True, recreate even without dimension check
            
        Returns:
            True if successful, False otherwise
        """
        class_name = f"WellnessContext_{version}"
        
        try:
            if not force_recreate:
                if self._verify_vector_dimension(class_name, expected_dimension):
                    return True
            
            logger.warning(f"Recreating class {class_name} due to dimension mismatch or force flag")
            
            # Delete existing class
            try:
                self.client.schema.delete_class(class_name)
                logger.info(f"Deleted existing class {class_name}")
            except Exception as e:
                logger.warning(f"Could not delete class {class_name}: {e}")
            
            # Recreate class
            return self.create_class_if_not_exists(version, expected_dimension)
            
        except Exception as e:
            logger.error(f"Failed to recreate class {class_name}: {e}")
            return False
    
    def get_class_info(self, version: str = "v1") -> Optional[Dict[str, Any]]:
        """Get information about a specific class version"""
        class_name = f"WellnessContext_{version}"
        
        try:
            schema = self.client.schema.get()
            for cls in schema.get('classes', []):
                if cls['class'] == class_name:
                    return cls
            return None
        except Exception as e:
            logger.error(f"Failed to get class info for {class_name}: {e}")
            return None
    
    def list_wellness_context_versions(self) -> list[str]:
        """List all available WellnessContext schema versions"""
        try:
            schema = self.client.schema.get()
            versions = []
            
            for cls in schema.get('classes', []):
                class_name = cls['class']
                if class_name.startswith('WellnessContext_'):
                    version = class_name.replace('WellnessContext_', '')
                    versions.append(version)
            
            return sorted(versions)
            
        except Exception as e:
            logger.error(f"Failed to list WellnessContext versions: {e}")
            return []