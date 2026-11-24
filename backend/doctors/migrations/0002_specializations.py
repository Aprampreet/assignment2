from django.db import migrations


def seed_specializations(apps, schema_editor):
    model = apps.get_model("doctors", "Specialization")
    for slug, name in [
        ("general-medicine", "General Medicine"),
        ("cardiology", "Cardiology"),
        ("dermatology", "Dermatology"),
        ("endocrinology", "Endocrinology"),
        ("neurology", "Neurology"),
        ("pediatrics", "Pediatrics"),
    ]:
        model.objects.using(schema_editor.connection.alias).get_or_create(slug=slug, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("doctors", "0001_initial")]
    operations = [migrations.RunPython(seed_specializations, migrations.RunPython.noop)]
