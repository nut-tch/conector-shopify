from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shopify_app", "0013_customer_company_nif"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderline",
            name="discount_amount",
            field=models.DecimalField(
                max_digits=10,
                decimal_places=2,
                default=0,
                verbose_name="Descuento línea",
            ),
        ),
    ]

