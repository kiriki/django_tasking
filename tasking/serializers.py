from rest_framework import serializers

from tasking.models import ModelTask


class TaskedObjectRelatedField(serializers.RelatedField):
    """
    A custom field to use for the `tagged_object` generic relationship.
    """

    def to_representation(self, value):
        """
        Serialize tagged objects to a simple textual representation.
        """
        if isinstance(value, TumblrBlog):
            serializer = TumblrBlogSerializer(value, context=self.context)
            return serializer.data
        raise Exception('Unexpected type of tagged object')


class ModelTaskSerializer(serializers.ModelSerializer):
    do_run = serializers.BooleanField(write_only=True, initial=True)

    # content_object = TaskedObjectRelatedField(read_only=True)

    class Meta:
        model = ModelTask
        fields = ('id', 'content_type', 'object_id', 'task', 'status', 'task_result', 'do_run')
        read_only_fields = ('task_result', 'status', 'object_id', 'content_type')

    def create(self, validated_data):
        data = validated_data.copy()

        if 'parent_lookup_object_id' in self.context:
            data['object_id'] = self.context['parent_lookup_object_id']
            data['content_type'] = self.context['parent_lookup_content_type']

        return super().create(data)


class TaskSerializerMonitorExtend(serializers.ModelSerializer):
    # content_object = TaskedObjectRelatedField(read_only=True)

    class Meta:
        model = ModelTask
        # fields = ('id', 'content_type', 'object_id', 'content_object', 'task_name', 'status', 'task_result')
        fields = ('id', 'content_type', 'object_id', 'task', 'status', 'task_result')
