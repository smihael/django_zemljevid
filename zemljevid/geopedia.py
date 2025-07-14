# Mapping field_type to Django model field types
FIELD_TYPE_MAPPING = {
    1: models.IntegerField,  # IDENTIFIER -> IntegerField
    3: models.BigIntegerField,  # NUMERIC -> BigIntegerField
    6: models.TextField,  # PLAINTEXT -> TextField
    8: tinymce_models.HTMLField,  # WIKITEXT -> TextField
    9: models.JSONField,  # BINARYREFERENCE -> JSONField
    10: models.DateTimeField,  # DATETIME -> DateTimeField
    13: models.TextField,  # STYLE -> TextField
    16: models.BooleanField,  # BOOLEAN -> BooleanField
    17: models.PointField,  # GEOMETRY -> PointField (GeoDjango field type)
}


class AbstractGeopediaModel(models.Model):
    """
    Abstract base class for Geopedia tables with dynamic field generation.
    """
    fid = models.AutoField(primary_key=True)
    geom = models.PointField(blank=True, null=True)
    
    # These should be overridden by subclasses
    table_id = None
    db_table = None
    

    _fields_generated = False

    class Meta:
        abstract = True
        managed = False
    
    @classmethod
    def generate_fields(cls):
        """
        Dynamically generate fields based on the Geopedia table structure.
        """

        if cls._fields_generated:
            return
    
        if cls.table_id is None:
            raise ValueError(f"table_id must be defined in {cls.__name__}")
            
        if cls.db_table is None:
            raise ValueError(f"db_table must be defined in {cls.__name__}")
            
        # Set the db_table in Meta
        cls._meta.db_table = cls.db_table
        
        # Get the geopedia_fields where the conditions are met
        query = """
        SELECT field_id, field_name, field_description, field_type
        FROM geopedia_fields f
        INNER JOIN geopedia_tables t ON f.table_id = t.table_id
        WHERE t.table_id = %s
          AND f.is_system = FALSE
          AND f.is_deleted = FALSE
        ORDER BY f.position
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [cls.table_id])
            fields = cursor.fetchall()

        # Dynamically add fields to model
        for field_id, field_name, field_description, field_type in fields:
            if field_name == "geometry" or field_name == "primaryGeometry":
                continue  # Skip geometry field as it's already defined

            field_class = FIELD_TYPE_MAPPING.get(field_type)

            if field_class is None:
                print(f"Warning: No field class found for type {field_type} in field {field_name}. Skipping.")
                continue  # Skip if no field class is found for the type

            # Map to db column
            column = f"f{field_id}"

            # Create the field with appropriate type, verbose_name, and help_text
            field = field_class(
                blank=True, null=True, db_column=column, verbose_name=field_name, help_text=field_description
            )

            if field_name == "Status spomenika":
                field.choices = MemorialStatus.choices
                print(f"Using MemorialStatus for field {field_name} with type {field_type}")
            
            # Add the field to the model dynamically
            field.contribute_to_class(cls, field_name)

        cls._fields_generated = True
